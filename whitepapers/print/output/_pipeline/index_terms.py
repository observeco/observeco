"""Index term list. Each entry: (regex to match in the body, index entry)."""
BRANDS = ["NTUC FairPrice","Sheng Siong","Cold Storage","Old Chang Kee","Ya Kun",
          "Tiger Balm","BreadTalk","Banyan Tree","Charles & Keith","Secretlab",
          "TWG","Grab","Carousell","Love Bonito","Khong Guan","Song Fa","Ka-Soh",
          "Tenderfresh","Creative Technologies","Thirsty4Balls","Mustafa","OSIM",
          "Shopee","Lazada","AlgoMerchant","Stuart Wright","Macrovalue","Singtel"]
AGENCIES = ["SingStat","EnterpriseSG","ACRA","IMDA","MOM","MTI","EDB","CPF","HDB","URA"]
CONCEPTS = [
 ("positioning","positioning"),("the ladder","ladder of the mind"),
 ("guerrilla","guerrilla (posture)"),("flanking","flanking (posture)"),
 ("defensive war","defence (posture)"),("offensive war","offence (posture)"),
 ("category creation","category creation"),("fragmented","fragmentation"),
 ("concentrated","concentration"),("Certificate of Entitlement","COE"),
 ("total fertility rate","fertility rate"),("value added per worker","value added per worker"),
 ("global engine","global engine"),("state engine","state engine"),
 ("domestic engine","domestic engine"),("referral","referral"),
 ("survival rate","business survival"),("entry cost","entry cost"),
 ("care economy","care economy"),("tuition","tuition"),
 ("hawker","hawkers"),("mental availability","mental availability"),
]
PEOPLE = [("Al Ries","Ries, Al"),("Jack Trout","Trout, Jack"),("Byron Sharp","Sharp, Byron"),
          ("Geoffrey Moore","Moore, Geoffrey"),("Philip Kotler","Kotler, Philip"),
          ("David Aaker","Aaker, David"),("Kevin Lane Keller","Keller, Kevin Lane"),
          ("April Dunford","Dunford, April"),("Gu Junhui","Gu Junhui"),
          ("Lee Kuan Yew","Lee Kuan Yew"),("Renée Mauborgne","Mauborgne, Renée"),
          ("W. Chan Kim","Kim, W. Chan")]

def entries():
    out=[]
    for b in BRANDS:   out.append((b,b))
    for a in AGENCIES: out.append((a,a))
    out.extend(CONCEPTS); out.extend(PEOPLE)
    return out
