"""Build the X Article draft payload (DraftJS content_state) for the Grab car marketplace article.

Outputs:
  - grab-article-draft.json  : the full POST /2/articles/draft request body
  - grab-article-curl.sh     : the exact curl command to submit it (run once credits exist)

The article body is converted from the approved markdown into DraftJS blocks.
"""
import json, os

base = "/Users/seanfzc/projects/observeco-main/content-writing/20260909"

# ---- Article metadata ----
TITLE = "Grab Now Sells Cars. Here's the Positioning Trap Hiding in It."

# ---- Build DraftJS blocks from the article ----
# Each block: {text, type, inline_style_ranges?, entity_ranges?}
# We keep it simple: unstyled paragraphs, header-one for section heads, blockquote for the pull-quote.
# Bold is applied via inline_style_ranges where the markdown used **...**.

def para(text, bold_spans=None):
    """text: plain string. bold_spans: list of (start, length) offsets to bold."""
    b = {"text": text, "type": "unstyled"}
    if bold_spans:
        b["inline_style_ranges"] = [{"offset": s, "length": l, "style": "bold"} for s, l in bold_spans]
    return b

def h1(text):
    return {"text": text, "type": "header-one"}

def quote(text):
    return {"text": text, "type": "blockquote"}

# Helper: find **bold** segments in a markdown-ish string and return (plain_text, bold_spans)
import re
def md_bold(s):
    """Convert **bold** markers to plain text + bold spans."""
    spans = []
    out = []
    pos = 0
    for m in re.finditer(r"\*\*(.+?)\*\*", s):
        out.append(s[pos:m.start()])
        out.append(m.group(1))
        spans.append((len("".join(out)) - len(m.group(1)), len(m.group(1))))
        pos = m.end()
    out.append(s[pos:])
    return "".join(out), spans

def P(s):
    """Paragraph block from a markdown string with **bold**."""
    t, spans = md_bold(s)
    return para(t, spans)

blocks = []

# --- Opening ---
blocks.append(P("Grab quietly opened a car sales site on 9 September 2026. **Car Marketplace by Grab** — at rentals.grab.com/car-marketplace — sells new and used cars to the general public, not just to Grab drivers."))
blocks.append(P("On launch evening it carried **44 cars** from eight sellers: 24 brand new and 20 used, priced from **S$11,800 to S$249,988**. Only 7 of the 44 run on petrol alone; the rest are electric, hybrid, or plug-in hybrid."))
blocks.append(P("The cheapest six are Grab's own retired private-hire cars. Every one has done between **527,000 and 719,000 km** — what an ordinary family car would take three decades to cover — and every one has a COE that expires in 2027."))
blocks.append(P("That's the story on the surface. But there's a deeper question underneath it, and it's the one almost nobody is asking."))
blocks.append(P("**Does Grab own the word for this?**"))

# --- Positioning basics ---
blocks.append(h1("The idea most people have never heard of: a brand is a word in the mind"))
blocks.append(P("Before we get to Grab, I need to teach you the single most useful idea in marketing — because it's the lens that makes this story make sense."))
blocks.append(P("Here it is: **a brand is not a logo, a product, or a company. A brand is a word in the customer's mind.**"))
blocks.append(P("When you hear \"Volvo,\" you think *safety*. When you hear \"Domino's,\" you think *30 minutes*. When you hear \"Grab,\" you think *your ride shows up*. That's not an accident. It's the whole game."))
blocks.append(P("The reason this matters is that the human mind has a short list for every category. Ask someone to name a ride-hailing app and they'll say Grab, maybe Gojek. Ask them to name a second one and they'll struggle. The mind keeps a short list of who's best at something — and the brands at the top of that list get the business."))
blocks.append(P("This is called **positioning**. And there's a brutal corollary that every business owner needs to understand:"))
blocks.append(quote("A category is not a position. \"Care\" is a category — a thousand companies do care, and none of them can be referred for it. \"The dementia specialist\" is a position — a specific word a person can put their name on."))
blocks.append(P("So when Grab launches a car marketplace, the question isn't \"can Grab sell cars?\" It's: **does \"buy a car\" fit the word Grab already owns?**"))

# --- The word Grab owns ---
blocks.append(h1("The word Grab owns — and the word it doesn't"))
blocks.append(P("Grab's word is built on **low-commitment, high-frequency** transactions. Your ride shows up. Your food arrives. Your groceries get delivered. These are small, frequent, trust-light purchases — you don't agonize over a S$15 ride."))
blocks.append(P("A car is the exact opposite. It's a **high-commitment, low-frequency** purchase. S$11,800 to S$249,988. Bought once every several years. The buyer agonizes for weeks. And the trust calculus is completely different — you're not trusting \"your ride shows up,\" you're trusting \"this car is worth S$100,000 and won't break next month.\""))
blocks.append(P("Here's the uncomfortable truth: **when you hear \"buy a used car in Singapore,\" the word that comes to mind is sgcarmart, not Grab.** sgcarmart owns that word. It's been the used-car marketplace for two decades. Grab is entering a category where a strong incumbent already owns the position."))
blocks.append(P("This is what positioning theory calls a **wall** — a category where a few names hold the money and the customer can only name them. You don't fight a wall head-on. You find the crack."))
blocks.append(P("So the real question becomes: **is there a crack? Is there something sgcarmart and Carousell don't give buyers that Grab can?**"))

# --- The gaps ---
blocks.append(h1("What buyers want that sgcarmart and Carousell don't give"))
blocks.append(P("I researched this carefully. Here's what Singapore car buyers actually want, and whether the incumbents provide it:"))
blocks.append(P("**1. Trust / verified history.** This is the big one. Buying a used car in Singapore is genuinely scary — there are documented odometer-tampering cases, and the buyer is told to \"inspect at your own risk.\" sgcarmart is a marketplace, not a guarantor. Carousell is worse — it's a general classifieds site with a documented scam problem. Neither stands behind the car."))
blocks.append(P("**2. EV battery health.** This is new and growing. As EVs flood the market, buyers want to know the battery's State of Health (SOH) — the single most expensive component. sgcarmart is only now adding an EV battery certification (EV NEXT, Aug 2026). It's a real, emerging gap."))
blocks.append(P("**3. Integrated financing.** Buying a car means arranging a loan, and the process is fragmented. sgcarmart already has a Smart Loan (2.78% for used cars) and a Quotz trade-in valuation. So this is a gap mainly for **Carousell**, not sgcarmart."))
blocks.append(P("**4. COE / depreciation clarity.** This is the most confusing part of buying a car in Singapore. A S$11,800 car with a COE expiring in 2027 is really a S$11,800 car for eight months, then a decision worth S$60,000–S$126,000 (the COE renewal PQP). Most buyers don't understand this until it's too late."))
blocks.append(P("**5. Inspection / warranty.** Independent inspection services exist, but they're separate, paid, and the buyer has to arrange them."))
blocks.append(P("**6. Standing behind the listing.** This is the deepest gap. A marketplace that *vouches* for the car would be worth paying for. Neither sgcarmart nor Carousell does this."))

# --- Does Grab close them ---
blocks.append(h1("Does Grab actually close these gaps?"))
blocks.append(P("This is where the analysis gets interesting — and where the stars either align or don't."))
blocks.append(P("**What Grab DOES provide:**"))
blocks.append(P("**Integrated financing.** The marketplace is run by GrabRentals, and it pushes **GXS AutoLoan** — Grab's own digital bank. This is a real gap-closer **vs Carousell** (which has no financing), though sgcarmart already has a Smart Loan. The seamlessness — financing through the same app you use for rides — is the edge."))
blocks.append(P("**Depreciation clarity.** Every listing shows an annual depreciation figure — the number Singapore buyers actually compare. That's genuinely useful, and most classifieds don't put it front and center."))
blocks.append(P("**What Grab does NOT provide:**"))
blocks.append(P("**Trust / verified history.** Here's the kicker. Grab's own terms say it does **not** vouch for the accuracy of any third-party listing — the mileage, the condition, the accident history. For the 38 cars sold by outside dealers, Grab is just the platform. The \"guaranteed mileage\" promise on its landing page applies only to Grab's own 6 cars (the G-Assured ones — which are the 527,000-km ex-fleet cars)."))
blocks.append(P("**EV battery certification.** No SOH certification on the marketplace."))
blocks.append(P("**Inspection / warranty.** The terms say \"inspect before you buy, as you would anywhere else.\""))
blocks.append(P("So here's the honest verdict: **Grab closes one real gap (depreciation clarity) and offers a seamless financing option (vs Carousell, though sgcarmart already has loans), but leaves the most important one — trust — wide open.** The one thing that would justify a new marketplace, verified trust, is exactly what Grab does not provide for most of its listings."))

# --- Track record ---
blocks.append(h1("The super-app track record — does this pattern predict success?"))
blocks.append(P("Grab has launched a lot of \"everyday everything\" verticals. The pattern is instructive:"))
blocks.append(P("**GrabShuttle (transit)** — launched 2016, **discontinued January 2020**. On-demand bus service, gone."))
blocks.append(P("**GrabTravel / hotels** — launched 2019, kept relaunching, now **GrabStays** (May 2026, via Nuitée). Still unproven."))
blocks.append(P("**GrabInsurance** — launched 2019 (ZhongAn JV). Active but niche."))
blocks.append(P("**GrabMart (grocery)** — launched 2019. **Growing** — grew 1.7× the rate of food delivery in Q2 2026."))
blocks.append(P("**GXS bank / GrabPay** — launched 2022. **Strong** — US$1.6B deposits in SG+MY, near-zero acquisition cost."))
blocks.append(P("The pattern is clear: **Grab wins where it extends an existing high-frequency habit** (food → groceries, rides → payments). It struggles where it **jumps into a low-frequency, high-commitment category** (transit was discontinued; travel keeps relaunching)."))
blocks.append(P("A car is the **lowest-frequency, highest-commitment** purchase of all. By Grab's own track record, that's the hardest kind of category for it to win."))

# --- Verdict ---
blocks.append(h1("So — is this a good idea?"))
blocks.append(P("Let me be honest, because that's the whole point of this piece."))
blocks.append(P("**The positioning case against:** Grab doesn't own the word for car-buying. sgcarmart does. Grab's trust is built on low-commitment, high-frequency transactions, and a car is the opposite. Its own track record says it struggles in low-frequency categories. And it's not even closing the one gap — trust — that would justify a new marketplace."))
blocks.append(P("**The positioning case for:** Grab is a *marketplace* company, and a car marketplace is a marketplace. It has the distribution (millions of users), the financing (GXS), and the data (it knows what cars drivers actually use). If it positions this as \"the platform that helps Singaporeans go electric\" — extending its mobility word — it's a coherent flank, not a jump. The EV angle is genuinely differentiated: all 20+ new cars are EV/hybrid, and Grab has a real driver ecosystem to feed."))
blocks.append(P("**The verdict:** the stars are **not** fully aligned. Grab closes two real gaps but leaves the trust gap open — and trust is the one thing that would make a new car marketplace worth it. It's a defensible flank if Grab leads with the EV/driver-ecosystem angle, but it's a category stretch if Grab positions it as \"Grab, now selling cars.\""))

# --- What this means ---
blocks.append(h1("What this means for your business"))
blocks.append(P("This isn't just a story about Grab. It's a masterclass in the difference between a category and a position — and that lesson applies to every small business in Singapore."))
blocks.append(P("**A category is not a position.** \"Care\" is a category. \"The dementia specialist\" is a position. \"Car marketplace\" is a category. \"The platform that helps you go electric\" is a position. The business that owns a specific word is the one that gets referred; the business that competes in a vague category competes on price."))
blocks.append(P("**Don't fight a wall head-on.** If a few names own the money in your category (like sgcarmart owns used cars), you don't enter and compete on price. You find the crack — the word, the niche, the gap they don't own."))
blocks.append(P("**The gap that matters is trust.** In a market that buys on referral (85% of Singapore buyers find solutions through personal referral), the business that a trusted person will vouch for is the one that wins. Grab's car marketplace is a case study in what happens when you enter a trust-driven category without providing the trust."))
blocks.append(P("Grab's car marketplace is not a story about a super-app. It's a story about **what happens when a brand enters a category where it doesn't own a word** — and whether it can find the crack. The same question is the one every small business should ask about its own market."))

# ---- Assemble DraftJS content_state ----
content_state = {
    "blocks": blocks,
    "entities": []
}

payload = {
    "title": TITLE,
    "content_state": content_state
}

# ---- Cover media (uploaded separately; media_id filled in after upload) ----
# The cover is 1200x675 (16:9), category tweet_image. After uploading via
# /2/media/upload, paste the returned media_id here and uncomment cover_media.
# payload["cover_media"] = {"media_category": "tweet_image", "media_id": "<MEDIA_ID>"}

# ---- Write files ----
draft_path = os.path.join(base, "grab-article-draft.json")
with open(draft_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

# Build the curl command (reads the JSON file)
curl = f"""#!/bin/bash
# Submit the Grab car marketplace article as a DRAFT on @1571keplerj.
#
# STEP 1 (FREE): upload the cover image -> returns a media_id
# STEP 2 (CHARGED): create the article draft with that media_id as cover
#
# Run ONLY after X API credits are added (currently: credits depleted).
# This creates a draft you review in the X app, then publish manually.

COVER="{base}/cover-grab-car.png"

echo "=== STEP 1: upload cover (FREE) ==="
MEDIA_JSON=$(~/go/bin/xurl -X POST /2/media/upload \\
  -H "Content-Type: application/json" \\
  -d '{{"media_category":"tweet_image","media_data":"$(base64 < "$COVER")"}}')
echo "$MEDIA_JSON"
MEDIA_ID=$(echo "$MEDIA_JSON" | /Users/seanfzc/.local/bin/python3.11 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{{}}).get('media_id',''))" 2>/dev/null)
echo "MEDIA_ID=$MEDIA_ID"

echo "=== STEP 2: create article draft (CHARGED) ==="
# Patch the media_id into the payload, then submit
/Users/seanfzc/.local/bin/python3.11 -c "
import json
p=json.load(open('{draft_path}'))
p['cover_media']={{'media_category':'tweet_image','media_id':'$MEDIA_ID'}}
json.dump(p, open('{draft_path}','w'), ensure_ascii=False, indent=2)
"
~/go/bin/xurl -X POST /2/articles/draft \\
  -H "Content-Type: application/json" \\
  -d @"{draft_path}"
"""
curl_path = os.path.join(base, "grab-article-curl.sh")
with open(curl_path, "w", encoding="utf-8") as f:
    f.write(curl)
os.chmod(curl_path, 0o755)

print("Wrote:", draft_path)
print("Wrote:", curl_path)
print("Blocks:", len(blocks))
print("Total chars:", sum(len(b["text"]) for b in blocks))
