import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib import rcParams
rcParams['font.family']='DejaVu Serif'

cats=[('Wholesale trade',494,'#1b6b57'),('Finance & insurance',436,'#1b6b57'),
      ('Education, health (state)',150,'#7a8ba6'),('Public admin (state)',116,'#7a8ba6'),
      ('Retail trade',58,'#b5651d'),('Food & beverage',32,'#b5651d')]
labels=[c[0] for c in cats]; vals=[c[1] for c in cats]; cols=[c[2] for c in cats]

fig,ax=plt.subplots(figsize=(4.15,3.1),dpi=300)
bars=ax.barh(range(len(vals))[::-1],vals,color=cols,height=0.62)
for y,v in zip(range(len(vals))[::-1],vals):
    ax.text(v+7,y,f'S${v}k',va='center',fontsize=8,fontweight='bold')
ax.set_yticks(range(len(labels))[::-1]); ax.set_yticklabels(labels,fontsize=8)
ax.set_xlabel('Value added per worker, S$ thousands (2024)',fontsize=8)
ax.set_xlim(0,560)
ax.spines[['top','right']].set_visible(False)
ax.tick_params(axis='x',labelsize=7.5)
ax.legend(handles=[mp.Patch(color='#1b6b57',label='Global engine'),
                   mp.Patch(color='#7a8ba6',label='State engine'),
                   mp.Patch(color='#b5651d',label='Domestic engine')],
          frameon=False,fontsize=7.5,loc='lower right')
ax.set_title('Value per worker, by engine',fontsize=10,loc='left',pad=8)
fig.text(0.02,0.015,'Source: SingStat, value added per worker by industry, 2024. Confidence: High.',fontsize=6.2,color='#555')
plt.tight_layout(rect=[0,0.04,1,1])
plt.savefig('fig-three-engines.pdf'); plt.savefig('fig-three-engines.png',dpi=300)
