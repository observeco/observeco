import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib import rcParams
rcParams['font.family']='DejaVu Serif'

# Industry map: value added by industry, S$bn, 2025 (from Part Three tables)
cats=[('Wholesale trade',146.5,'#1b6b57'),('Manufacturing',137.6,'#1b6b57'),
      ('Finance & insurance',104.2,'#1b6b57'),('Transport & storage',60.1,'#1b6b57'),
      ('Info & communications',47.1,'#1b6b57'),('Professional services',41.8,'#1b6b57'),
      ('Construction',30.0,'#7a8ba6'),('Real estate',22.2,'#7a8ba6'),
      ('Health & social services',20.7,'#7a8ba6'),('Admin & support',18.4,'#7a8ba6'),
      ('Education',18.4,'#7a8ba6'),('Public admin & defence',17.6,'#7a8ba6'),
      ('Retail trade',9.0,'#b5651d'),('Other services',8.6,'#b5651d'),
      ('Food & beverage',7.6,'#b5651d'),('Arts & entertainment',7.6,'#b5651d'),
      ('Accommodation',5.6,'#b5651d'),('Agriculture, fishing, mining',0.2,'#b5651d')]
labels=[c[0] for c in cats]; vals=[c[1] for c in cats]; cols=[c[2] for c in cats]

fig,ax=plt.subplots(figsize=(4.15,4.6),dpi=300)
bars=ax.barh(range(len(vals))[::-1],vals,color=cols,height=0.62)
for y,v in zip(range(len(vals))[::-1],vals):
    ax.text(v+2,y,f'S${v:.1f}bn',va='center',fontsize=6.5,fontweight='bold')
ax.set_yticks(range(len(labels))[::-1]); ax.set_yticklabels(labels,fontsize=6.5)
ax.set_xlabel('Value added, S$ billions (2025)',fontsize=7.5)
ax.set_xlim(0,165)
ax.spines[['top','right']].set_visible(False)
ax.tick_params(axis='x',labelsize=7)
ax.legend(handles=[mp.Patch(color='#1b6b57',label='Global engine'),
                   mp.Patch(color='#7a8ba6',label='State engine'),
                   mp.Patch(color='#b5651d',label='Domestic engine')],
          frameon=False,fontsize=6.5,loc='lower right')
ax.set_title('The industry map: value added by industry',fontsize=9,loc='left',pad=8)
fig.text(0.02,0.012,'Source: SingStat, gross value added by industry, 2025. Confidence: High.',fontsize=5.8,color='#555')
plt.tight_layout(rect=[0,0.03,1,1])
plt.savefig('fig-industry-map.pdf'); plt.savefig('fig-industry-map.png',dpi=300)
print('wrote fig-industry-map')
