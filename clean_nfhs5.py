"""Cleaning and preprocessing of the NFHS-5 state/UT fact sheet file (long format).
Input : nfhs5_states.csv  (state, state_code, indicator, nfhs5_urban, nfhs5_rural, nfhs5_total, nfhs4_total)
Output: nfhs5_states_clean_long.csv, nfhs5_cvd_dm_analysis.csv, cleaning_log.json, figures"""
import pandas as pd, numpy as np, re, json, hashlib
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
SRC='nfhs5_states.csv'; L={}
raw=pd.read_csv(SRC); L['sha256']=hashlib.sha256(open(SRC,'rb').read()).hexdigest()[:16]
VALS=['nfhs5_urban','nfhs5_rural','nfhs5_total','nfhs4_total']
# ---- Step 1 profile
L['rows']=len(raw); L['cols']=raw.shape[1]; L['geographies']=int(raw.state.nunique()); L['indicators']=int(raw.indicator.nunique())
L['miss_raw']={c:int(raw[c].isna().sum()) for c in raw.columns}
L['exact_dups']=int(raw.duplicated().sum()); L['key_dups']=int(raw.duplicated(['state','indicator']).sum())
df=raw.copy()
# ---- Step 2 standardise: strip, indicator number, unit, footnote marks, clean label
df['state']=df.state.str.strip(); df['indicator']=df.indicator.str.strip()
df['ind_no']=df.indicator.str.extract(r'^(\d+)\.')[0].astype(int)
lab=df.indicator.str.replace(r'^\d+\.\s*','',regex=True)
df['unit']=lab.str.extract(r'\(([^()]*)\)\s*$')[0]
lab_nounit=lab.str.replace(r'\s*\(([^()]*)\)\s*$','',regex=True)
# footnote digits: digits glued to a word/closing bracket at the end of the label, or "16, 17"
fn_mask=lab_nounit.str.contains(r'(?<=[A-Za-z\)])\d{1,2}(?:,\s*\d{1,2})*\s*$')
L['labels_with_footnote']=int(df.drop_duplicates('ind_no').assign(m=fn_mask.loc[df.drop_duplicates('ind_no').index]).m.sum())
df['label']=lab_nounit.str.replace(r'(?<=[A-Za-z\)])\d{1,2}(?:,\s*\d{1,2})*\s*$','',regex=True).str.strip()
# mid-label footnotes e.g. "source1" handled in line above only at end; strip those that precede " (" were moved by unit removal
df['unit']=df.unit.replace({'%':'percent'})
L['units']=df.drop_duplicates('ind_no').unit.value_counts().to_dict()
# state names
rename={'NCT Delhi':'Delhi'}; df['state']=df.state.replace(rename).str.replace('&','and',regex=False)
L['state_names_changed']=int((raw.state.str.strip()!=df.state).sum()//131)
# definition variants: same indicator number, different wording across states
var=df.groupby('ind_no').label.nunique(); L['indicators_with_label_variants']=var[var>1].index.tolist()
df['definition_variant']=''
for n in var[var>1].index:
    m=df.ind_no==n; df.loc[m,'definition_variant']=df.loc[m,'label']
    L['variant_%d'%n]=df[m].groupby('label').state.apply(lambda x:len(x)).to_dict()
    # harmonised label keeps the wider wording out; analysis must not pool the variants silently
# ---- Step 3 duplicates (none expected) - verify keys
L['dups_removed']=int(df.duplicated(['state','ind_no']).sum()); df=df.drop_duplicates(['state','ind_no'])
# ---- Step 4 sex assignment for repeated labels (factsheet layout: first block women, second block men)
grp=df.drop_duplicates('ind_no').groupby('label').ind_no.apply(sorted)
dupl=grp[grp.apply(len)>1]; L['repeated_labels']={k:v for k,v in dupl.items()}
df['group']='All'
for k,v in dupl.items():
    df.loc[df.ind_no==v[0],'group']='Women (15+)'; df.loc[df.ind_no==v[1],'group']='Men (15+)'
L['groups_assigned']=int(len(dupl))
# explicit sex from label text for others
df.loc[df.label.str.contains(r'\bWomen\b|\bwomen\b') & (df.group=='All'),'group']='Women'
df.loc[df.label.str.contains(r'\bMen\b') & (df.group=='All'),'group']='Men'
# ---- Step 5 range / logic checks
pct=df.unit=='percent'
L['pct_out_of_range']=int(((df.loc[pct,VALS]<0)|(df.loc[pct,VALS]>100)).sum().sum())
L['negative_values']=int((df[VALS]<0).sum().sum())
L['zeros']={c:int((df[c]==0).sum()) for c in VALS[:3]}
m=df.dropna(subset=VALS[:3])
lo=m[VALS[:2]].min(axis=1); hi=m[VALS[:2]].max(axis=1)
tot_bad=m[(m.nfhs5_total<lo-0.05)|(m.nfhs5_total>hi+0.05)]
L['total_outside_urban_rural']=int(len(tot_bad)); L['complete_rows_checked']=int(len(m))
# component checks: elevated (incl medicine) >= mild + moderate/severe ; high-or-very-high >= high+very high
def chk(a,b,c,name):
    w=df.pivot_table(index=['state'],columns='ind_no',values='nfhs5_total')
    sub=w[[a,b,c]].dropna(); bad=sub[sub[c]<sub[a]+sub[b]-0.15]
    L[name]={'checked':int(len(sub)),'violations':int(len(bad))}
for (a,b,c,n) in [(99,100,101,'sugar_women'),(102,103,104,'sugar_men'),(105,106,107,'bp_women'),(108,109,110,'bp_men')]: chk(a,b,c,'logic_'+n)
# outliers: IQR check inside each indicator on total
def iqr_flag(s):
    q1,q3=s.quantile([.25,.75]); i=q3-q1; return (s<q1-3*i)|(s>q3+3*i)
df['outlier_flag']=df[df.state!='India'].groupby('ind_no').nfhs5_total.transform(iqr_flag).fillna(False).astype(int)
L['outliers_flagged']=int(df.outlier_flag.sum())
# ---- Step 6 missing data: classify, do NOT impute
nat=df[df.state=='India']; L['india_rows_missing_total']=int(nat.nfhs5_total.isna().sum())
df['miss_urban']=df.nfhs5_urban.isna().astype(int); df['miss_rural']=df.nfhs5_rural.isna().astype(int)
df['miss_total']=df.nfhs5_total.isna().astype(int); df['miss_nfhs4']=df.nfhs4_total.isna().astype(int)
L['miss_total_with_both_ur']=int(((df.miss_total==1)&(df.miss_urban==0)&(df.miss_rural==0)).sum())
L['miss_ur_but_total_present']=int((((df.miss_urban==1)|(df.miss_rural==1))&(df.miss_total==0)).sum())
by_state=df[df.state!='India'].groupby('state')[['miss_urban','miss_rural','miss_total']].sum().sum(axis=1).sort_values(ascending=False)
L['miss_by_state_top']=by_state.head(8).to_dict()
L['miss_clean']={c:int(df[c].isna().sum()) for c in VALS}
# nfhs4 structurally absent for indicators not collected in NFHS-4
nf4=df.drop_duplicates('ind_no').set_index('ind_no'); allna=df.groupby('ind_no').nfhs4_total.apply(lambda s:s.isna().all()); L['indicators_without_nfhs4']=int(allna.sum())
# ---- Step 7 derived variables
df['gap_urban_minus_rural']=(df.nfhs5_urban-df.nfhs5_rural).round(1)
df['change_nfhs4_to_5']=(df.nfhs5_total-df.nfhs4_total).round(1)
# ---- Step 8 selection for the project + wide format
KEY={105:'bp_mild',106:'bp_mod_severe',107:'bp_elevated_or_medicine',108:'bp_mild',109:'bp_mod_severe',110:'bp_elevated_or_medicine',
     99:'sugar_high',100:'sugar_very_high',101:'sugar_high_or_medicine',102:'sugar_high',103:'sugar_very_high',104:'sugar_high_or_medicine'}
k=df[df.ind_no.isin(KEY)].copy(); k['measure']=k.ind_no.map(KEY)
k['condition']=np.where(k.ind_no<105,'blood_sugar','blood_pressure')
wide=k.pivot_table(index=['state','condition','group','measure'],values=['nfhs5_urban','nfhs5_rural','nfhs5_total'],aggfunc='first').reset_index()
wide['gap_urban_minus_rural']=(wide.nfhs5_urban-wide.nfhs5_rural).round(1)
wide['high_risk_flag']=0
for (cond,grp_),g in wide[(wide.measure.str.endswith('medicine'))&(wide.state!='India')].groupby(['condition','group']):
    thr=g.nfhs5_total.quantile(.75); wide.loc[g.index,'high_risk_flag']=(g.nfhs5_total>=thr).astype(int)
L['analysis_rows']=len(wide)
# ---- Step 9 validate against national row & export
nat=wide[(wide.state=='India')&(wide.measure.str.endswith('medicine'))][['condition','group','nfhs5_urban','nfhs5_rural','nfhs5_total']]
L['india_check']=nat.round(1).to_dict('records')
st=wide[(wide.state!='India')&(wide.measure.str.endswith('medicine'))]
L['state_range']={f"{c}|{g}":[round(float(x.nfhs5_total.min()),1),round(float(x.nfhs5_total.max()),1),x.loc[x.nfhs5_total.idxmin(),'state'],x.loc[x.nfhs5_total.idxmax(),'state']] for (c,g),x in st.groupby(['condition','group'])}
L['final_rows_long']=len(df); L['final_cols_long']=df.shape[1]
out=['state','state_code','ind_no','label','unit','group']+VALS+['gap_urban_minus_rural','change_nfhs4_to_5','outlier_flag','definition_variant','miss_urban','miss_rural','miss_total','miss_nfhs4']
df[out].to_csv('nfhs5_states_clean_long.csv',index=False); wide.to_csv('nfhs5_cvd_dm_analysis.csv',index=False)
json.dump(L,open('cleaning_log.json','w'),indent=1,default=str)
print(json.dumps(L,indent=1,default=str))
# ---- figures
NAVY='#1F3A5F';TEAL='#2A7F8E';GREY='#999999'
s=df[df.state!='India'].groupby('state')[['miss_urban','miss_rural','miss_total']].sum().sum(axis=1).sort_values()
fig,ax=plt.subplots(figsize=(8.6,4.6),dpi=200); ax.barh(s.index,s.values,color=[TEAL if v<30 else NAVY for v in s.values])
ax.set_xlabel('Missing values among 393 cells per state (131 indicators x urban, rural, total)',fontsize=8); ax.tick_params(labelsize=6.5)
ax.spines[['top','right']].set_visible(False); ax.set_title('Missing NFHS-5 values by state or union territory (real data)',fontsize=9,color=NAVY)
plt.tight_layout(); plt.savefig('missing_state.png'); plt.close()
w=wide[(wide.state!='India')&(wide.measure=='bp_elevated_or_medicine')]
fig,ax=plt.subplots(1,2,figsize=(8.6,3.6),dpi=200,sharey=True)
for a,g,col in zip(ax,['Women (15+)','Men (15+)'],[TEAL,NAVY]):
    x=w[w.group==g].dropna(subset=['nfhs5_urban','nfhs5_rural']); a.scatter(x.nfhs5_rural,x.nfhs5_urban,color=col,s=16)
    lim=[x[['nfhs5_urban','nfhs5_rural']].min().min()-1,x[['nfhs5_urban','nfhs5_rural']].max().max()+1]; a.plot(lim,lim,color=GREY,lw=.8,ls='--')
    a.set_title(g,fontsize=9,color=NAVY); a.set_xlabel('Rural (%)',fontsize=8); a.tick_params(labelsize=7); a.spines[['top','right']].set_visible(False)
ax[0].set_ylabel('Urban (%)',fontsize=8); fig.suptitle('Elevated blood pressure or on treatment: urban vs rural, by state (cleaned data)',fontsize=9,color=NAVY)
plt.tight_layout(); plt.savefig('bp_urban_rural.png'); plt.close()
