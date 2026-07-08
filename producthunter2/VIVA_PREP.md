# Viva Prep — Product Hunter Agent (v2)

Likely sawalat aur unke jawabat. Practice kar lena confidently.

---

## Concept

**Q: Yeh agent karta kya hai?**

Yeh trending / best-selling products dhoondta hai (Amazon best-sellers se),
aur phir har product ko ek "opportunity score" deta hai — yaani yeh product
bechne layak hai ya nahi. Sirf popular products ki list nahi deta, balke
smartly rank karta hai ke kaunsa product sabse achha business opportunity
hai.

**Q: "Product scoring" kya hoti hai?**

Har product ko teen cheezon pe judge karte hain:
1. **Demand** — log ise kitna khareed rahe hain? (best-seller rank, sales
   volume, rating se pata chalta hai)
2. **Competition** — market kitna crowded hai? Agar kisi product ke 50,000
   reviews hain to bohat sellers already hain — compete karna mushkil. Kam
   reviews wala product = kam competition = better opportunity.
3. **Profit** — price sweet spot mein hai? $15–60 wale products best margin
   dete hain reseller ke liye.

In teenon ko weighted formula se mila kar ek final 0–100 score banate hain,
aur products ko best-first sort kar dete hain.

**Q: Score ka formula kya hai?**

`opportunity = 0.45 × demand + 0.35 × competition + 0.20 × profit`

Demand ko sabse zyada weight isliye diya ke "bikega ya nahi" sabse important
hai. Yeh pura formula `scoring.py` mein hai — main viva mein exact math
dikha sakta hoon.

---

## Technical

**Q: AI (LLM) kyun use nahi kiya scoring ke liye?**

Rule-based formula deliberately choose kiya kyunki:
1. Hamesha kaam karta hai — na Ollama chahiye na internet.
2. 100% explainable hai — main exact formula point kar sakta hoon.
3. Fast hai — instantly hundreds of products score kar deta hai.
LLM slow hota (har product pe ek call) aur non-deterministic — viva ke liye
reliable rule-based behtar hai.

**Q: Free kaise hai? Amazon ka data free mein kaise mil raha hai?**

Do tareeqe hain:
1. RapidAPI ka "Real-Time Amazon Data" — free tier 100 requests/month, koi
   credit card nahi. User apni key GUI mein paste karta hai.
2. Agar key na ho ya API fail ho jaye, to built-in demo data use hota hai —
   isliye app kabhi crash nahi karti, viva mein hamesha chalti hai.

**Q: Email scraper mein to keyless scraping ki thi, yahan API key kyun?**

Amazon ka anti-bot protection Google Maps se bohat zyada aggressive hai. Raw
keyless scraper bar bar toot jata, demo unreliable ho jata. Isliye free
RapidAPI key hi honest "free lekin reliable" jawab hai.

**Q: Threading kaise handle ki?**

Fetching slow hai (network), isliye `HuntWorker` (QObject) ko separate
QThread pe move kiya — GUI freeze nahi hoti. Results Qt signals ke through
wapas aate hain. Yeh same pattern hai jo baaki agents (email scraper) mein
use hua.

**Q: Agar future mein Amazon ki official API add karni ho to?**

Code already ready hai. `product_fetcher.py` mein ek `provider` dispatch
hai aur ek commented slot `_fetch_from_amazon_paapi()` ke liye. Sirf ek naya
function likhna hoga jo `Product` objects return kare, aur ek `elif` branch.
Baaki kuch change nahi hoga — scoring, GUI, export sab same rahega, kyunki
har source same `Product` objects deta hai. Yeh clean architecture ka faida
hai.

---

## Integration

**Q: Yeh agent baaki FYP se kaise connected hai?**

Do integration points hain:
1. **Excel export** — shortlisted products ek formatted Excel report mein.
2. **"Write Content" button** — top product ko directly Content Scripting
   agent ko bhej deta hai, jo uski marketing copy / ad likhta hai. Ek click
   mein "winning product mila" se "uski ad copy likhi ja rahi hai" tak.

---

## Limitations (agar poochein "improve kya karoge?")

- Free RapidAPI 100 req/month hai — heavy use ke liye paid plan chahiye
- Scoring relative opportunity rank karti hai, actual sales predict nahi
  karti — yeh ek estimate hai, guarantee nahi
- Profit score price-band pe based hai; asli sourcing cost nahi janta (uske
  liye supplier-side data chahiye — future addition)

Yeh limitations honestly batana better hai — examiners genuine understanding
ko value karte hain over "sab perfect hai" claims.
