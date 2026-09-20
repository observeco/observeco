import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib import rcParams
rcParams['font.family']='DejaVu Serif'

# Four demographic waves (from the demographics chapter tables)
# Wave 1: fertility collapse — TFR 0.87 (2025), births 27,393 (-11.1%)
# Wave 2: ageing — citizens 65+ at 20.7% (up from 13.1% in 2015)
# Wave 3: shrinking household — seniors living alone 88,000
# Wave 4: foreign workers — 1.23M foreign workers, 317,000 helpers

fig, axes = plt.subplots(2, 2, figsize=(4.15, 3.4), dpi=300)
fig.suptitle('The four demographic waves', fontsize=9, x=0.02, ha='left')

# Wave 1: TFR collapse
ax = axes[0,0]
ax.bar(['2015','2025'], [1.24, 0.87], color=['#7a8ba6','#1b6b57'], width=0.5)
ax.set_title('Fertility: TFR fell to 0.87', fontsize=6.5, loc='left')
ax.set_ylabel('Total fertility rate', fontsize=5.5)
ax.tick_params(labelsize=5.5)
ax.spines[['top','right']].set_visible(False)

# Wave 2: ageing
ax = axes[0,1]
ax.bar(['2015','2025'], [13.1, 20.7], color=['#7a8ba6','#1b6b57'], width=0.5)
ax.set_title('Ageing: 65+ rose to 20.7%', fontsize=6.5, loc='left')
ax.set_ylabel('Citizens aged 65+, %', fontsize=5.5)
ax.tick_params(labelsize=5.5)
ax.spines[['top','right']].set_visible(False)

# Wave 3: shrinking household
ax = axes[1,0]
ax.bar(['Seniors alone'], [88], color='#1b6b57', width=0.4)
ax.set_title('Shrinking household: 88,000 seniors live alone', fontsize=6.5, loc='left')
ax.set_ylabel('Seniors living alone, thousands', fontsize=5.5)
ax.tick_params(labelsize=5.5)
ax.spines[['top','right']].set_visible(False)

# Wave 4: foreign workers
ax = axes[1,1]
ax.bar(['Foreign workers','Domestic helpers'], [1.23, 0.317], color=['#1b6b57','#7a8ba6'], width=0.5)
ax.set_title('Foreign workers: 1.23M, incl. 317k helpers', fontsize=6.5, loc='left')
ax.set_ylabel('Millions', fontsize=5.5)
ax.tick_params(labelsize=5.5)
ax.spines[['top','right']].set_visible(False)

fig.text(0.02,0.012,'Source: SingStat, Population.gov.sg, MOM. Confidence: High.',fontsize=5.8,color='#555')
plt.tight_layout(rect=[0,0.03,1,0.95])
plt.savefig('fig-four-waves.pdf'); plt.savefig('fig-four-waves.png',dpi=300)
print('wrote fig-four-waves')
