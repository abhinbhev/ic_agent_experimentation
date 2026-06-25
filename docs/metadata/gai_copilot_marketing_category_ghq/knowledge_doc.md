# Domain
Strategy and Insights (or S&I) is a domain within Marketing Analytis which deals with Brand perception and consumption in the market. The two broad studies that fall under this umbrella are
- Brand Guidance: linked with brand perception in the market across various demographics
- Category: deals with **consumption metrics** and patterns at brand or category level across various demograhics

S&I helps understand the whitespaces in the market and the JTBDs (Jobs to be done) for brands based on survey based metrics correlated with other tangible factors.

# Usecase
The purpose of the POS program is to grow the beer category, not individual consumption behavior. POS metrics are setup to understand the behavior of cosumers above the Legal Drinking Age (LDA) of the specific country. The KPIs are Participation, Occasions and Servings. The most important type of analysis is at demographic cohort levels.

# Usecase definitions

This section defines all KPIs and measures available in the dataset.
Each entry includes **definition**, **scale or calculation rule**, and a **sample query** at brand–country level.

### **Participation**
- **Definition:** % of consumers who have consumed the category within a defined time period.
- **Calculation rule:** % of Category Drinkers = Number of P4W Category Drinkers / Total LDA+ Population
- **Example query:** *What is the Participation of Budweiser in US in FY 2024?*

### **Occasions**
- **Definition:** The number of times consumers engage with the category in a given time period.
- **Calculation rule:** # of Occasions per week = Total # of P7D (BEER) Occasions / # P4W (BEER) Drinkers
- **Example query:** *What are the Occasions of Brahma in Brazil in FY 2024?*

### **Servings**
- **Definition:** Average quantity consumed per occasion (standardized into serving sizes: 330ml beer, 300ml rtd/cider, 50ml spirits, 175ml wine).
- **Calculation rule:** # of Servings per Occasion = Number of Servings / Number of Occasions
- **Example query:** *What are the Servings of Beer in Mexico in FY 2024?*


# Analysis Templates roadmap

## What has been implemented?

### Analysis Template (AT) Definition
The assistant maps user queries to one of four Analysis Templates (functions).
Each Analysis Template represents a specific scope of analysis, and parameters are always populated as lists, even when only a single value is provided.

---

### Available Analysis Templates
1. **`get_factual_analysis`**
    - Purpose: Default template for factual questions such as *What*-type requests, KPI retrieval, and cohort-level breakdowns.
    - Triggers: Keywords and phrases such as: *“participation of brand X”*, *“occasions of category Y”*, *“servings in M1 markets”*, *“POS of zone X”*.
    - Output: Returns factual KPI values or breakdowns at the specified analysis level (direct, zone_aggregate, market_maturity_aggregate).
    - Special Rule: If no category is mentioned, default to `category = 'beer'`.
    - Behavior: Always set `analysis_level` based on scope:
     - `direct` if specific brand(s) in a specific market are requested.
     - `zone_aggregate` if specific category in a specific zone is requested.
     - `market_maturity_aggregate` if specific category in a specific market maturity level(M1, M2, M3) is requested.

2. **`get_pos_country_highlights`**
    - Purpose: Used when the query requests country-level highlights or overall performance without specifying any brand or KPI.
    - Triggers: Keywords such as *“country highlights”*, *“overview of <country>”*, *“how is <country> doing”*.
    - Output: Returns high-level summary for the requested country.

---

### Function Selection Priority
The selection of Analysis Template follows strict priority order:
1. If query is about **country-level highlights or overview** without a brand or KPI → select `get_pos_country_highlights`.
2. All other cases (factual KPI requests, comparisons, rankings, imagery, cohort slicing, time trends) → select `get_factual_analysis`.

---

### Parameters and Extraction Rules
All extracted parameters must be passed as lists of values. When queries imply “all” values, the keyword `across` must be used.

- **year**: Extract explicit years (e.g., `'2023'`, `'2024'`, or `'2023,2024'`).
- **period**: Extract explicit time periods. Valid values: `'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Q1', 'Q2', 'Q3', 'Q4', 'H1', 'H2', 'FY'`.
- **period_type**: Extract rolling or annualized indicators. Valid values: `'QTR', 'YTD', 'half year', 'full year', 'R3M', 'R6M', 'R9M', 'R12M'`. Example: “rolling 12 months” → `'R12M'`.
- **country**: Must be selected from the fixed exhaustive list:
  `['argentina', 'belgium', 'bolivia', 'brazil', 'canada', 'chile', 'china', 'colombia', 'dominican republic', 'ecuador', 'el salvador', 'france', 'germany', 'guatemala', 'honduras', 'italy', 'mexico', 'mozambique', 'netherlands', 'nigeria', 'panama', 'peru', 'south africa', 'south korea', 'tanzania', 'uk', 'uruguay', 'us', 'zimbabwe']`
- **brand**: Extracted brand names exactly as provided in query.
- **zone**: Must be one of `[AFR, EU, APAC, NAZ, SAZ, MAZ]`. If query implies all zones, use `'across'`.
- **market_maturity**: Must be one of `[M1, M2, M3]`. If query implies all maturities, use `'across'`.
- **kpi**: Must be selected from the exhaustive list: `['participation', 'occasions', 'servings']`
- **macrocategory**: Must be one of `['non alc bevs', 'alc bevs informal', 'formal + informal alc bevs', 'alc bevs']` when explicitly mentioned.
- **manufacturer**: Must be selected from the exhaustive list: `['11 cider house', '11 do brasil', '361 degrees', '44 degrees', '503 distilling', 'a.j. vierci', 'abb.st.remy', 'abinbev', 'accolade', 'ace beverage group', 'adnams', 'ae brands kor', 'afrb', 'agrial', 'ailar korea', 'al amoudi', 'al capone', 'alberto bellesso', 'aldi', 'aleanna', 'alianca', 'All', 'allagash brewing', 'alpine beer company', 'amazing brewing company', 'amsterdam brewery', 'anapa', 'ancestral', 'anciens du seminaire', 'andrew peller', 'antillanca', 'aquilini brands', 'arbor brasil', 'arizona', 'arterra wines canada', 'asa branca', 'asahi', 'ashland', 'aston manor cider', 'athletic brewing', 'atwater', 'augustiner muenchen', 'azuma kirin', 'bacardi', 'bahia', 'baracho', 'barkov', 'barrio', 'bavaria nv', 'bavik', 'be long de meriti', 'beam suntory', 'beaus allntrl brewng', 'beavertown brewery', 'beb. bolivianas bbo', 'bebidas asteca', 'bebidas bolivianas bbo', 'bebidas chiamuleras', 'bebidas del paraguay', 'bebidas duelo', 'bebidas mdm', 'bebidas rodrigues e silva', 'beerbeltkorea imp', 'beerteke', 'berentzen', 'bernard hayot', 'bestbuy & beverage', 'beverage brands', 'bier & wein', 'biere sans alcool', 'bieres de chimay', 'bierhaus brewing', 'big rock brewery', 'bitburger', 'biz f&b korea imp', 'bk', 'black fly beverage', 'black sheep', 'blest', 'blondine', 'bodega bay', 'bodega graffigna', 'bodega norton', 'bodega rutini wines', 'bodegas balbo', 'bodegas catena zapata', 'bodegas chandon', 'bodegas dante robino', 'bodegas esmeralda', 'bodegas lavaque', 'bodegas salentein', 'bodegas y viñedos lopez', 'boituva', 'bold rock', 'booker', 'borco', 'boston beer co', 'bota fox', 'bowen island brwg co', 'br.bockor', 'br.dubuisson', 'br.friart', 'br.lefebvre', 'br.lindemans', 'br.orval', 'br.roman', 'br.st bernard', 'brassaria ampolis', 'brasserie goudale', 'brasseurs rj', 'brasseurs sans glutn', 'braxzz bv', 'brew house', 'brewdog', 'brick brewing', 'britvic', 'broue alliance', 'brown forman', 'bruce ashley group', 'brumado', 'budvar brewery', 'buffalo', 'buoy', 'buruguru', 'c & c group', 'c.n.b.n', 'c.r.s. brands', 'cahaba brewing', 'campari', 'canadian club whisky company', 'canarchy', 'canella', 'cannolificio mongibello', 'canteen', 'capel', 'cardozzano', 'cariboo brewing', 'carlsberg', 'carlsberg marston bc', 'carolina wine brand', 'casa di conti', 'casarena bodegas', 'catawba', 'catuaba', 'ccb', 'ccu', 'celliers associes', 'central cervecera', 'central city brewer', 'cepas arg', 'cereser', 'cerpa', 'cerv. nacional potosi', 'cerv.artesanal', 'cervecería asunción', 'cerveceria centroamericana', 'cervecerias peruanas backus', 'cervejaria bamboa', 'cervejaria cidade imperial', 'champion', 'charles jacquin', 'china resources snow', 'cía cervecera boliviana sa', 'cia. brasileira de bebidas pre', 'ciber', 'cider of sweden', 'co.indl.cervecera', 'coca cola', 'coldstream', 'colio estate wines', 'collective arts brewing', 'college street brewhouse', 'colonia', 'compañía pisquera de chile', 'concha y toro', 'constellation', 'contini', 'coop ale works', 'coop vitivinifruticola de la riojana', 'corby distilleries', 'cordier by invivo', 'corinthian brands', 'coronado', 'country boy brewing', 'covisan', 'creature comforts brewing', 'crosby lake', 'cruz de piedra', 'cvb_brij_der_tr.', 'd g yuengling', 'daedonggang', 'daily juice', 'damm', 'damoiseau', 'de kuyper', 'deep eddy distilling', 'del valle', 'dellepiane', 'delta corporation', 'desa', 'destilaria hambre', 'destilerias mg', 'devil's peak', 'dia retailer', 'diageo', 'dialcool', 'diego zamora', 'distribuidora gloria', 'diuka', 'dormoy', 'dr. gerald rauch', 'dr. oetker / radeberger', 'driftwood brewery', 'drink four brewing', 'drink mom', 'drinks capital', 'drty drinks', 'dry fly distilling', 'duvel', 'e&j gallo', 'east african spirits (t) ltd.', 'eclor', 'eders', 'einbecker', 'entreprise ivoire delice', 'equator breweries', 'erdinger', 'espadafor', 'estabs vitivinicolas escorihuela', 'etnia', 'exile brewing', 'extra', 'f. antonio chiamulera', 'familia millan', 'familia schroeder', 'familia zuccardi', 'fante', 'fecovita', 'feldschlobchen ag', 'felix solis', 'fifco', 'finca la celia', 'five drinks co', 'flying embers', 'fopix', 'forst', 'fort point', 'founders original', 'frascati', 'fresca', 'frost imp', 'full', 'funkin', 'gadotti', 'gallo', 'garbin', 'garcia carrion', 'gaz sake spritz', 'geloso', 'georgetown brewing', 'georgian bay gin', 'gerim spirits co', 'germany brewery imports', 'ginta', 'glenmore', 'global brands', 'glolens', 'golden blue', 'good people brewing', 'gouguenheim winery', 'grands chais de france', 'great lakes brewing', 'great western', 'greene king', 'grupo imperial', 'grupo penaflor', 'grupo petropolis', 'grupo riquelme', 'guinness', 'gulpener', 'h weston', 'haacht', 'habeco', 'halewood', 'halvemaan', 'handelsmarken', 'happy dad', 'harboe', 'hardenberg wilthen', 'hardz', 'hb imp', 'heaven hill', 'heineken', 'henkell freixenet', 'herman jansen', 'het anker', 'highland brewery', 'hijos de rivera', 'hitejinro.co', 'hop city brewing co', 'house of monaco', 'huss brewing', 'huyghe', 'i.magia', 'i.r.l.', 'ice box', 'indel', 'independent liquor', 'indulge korea', 'industrias barlix', 'innis & gunn', 'inter k imp', 'intercontinental distillers ltd', 'island', 'j.llorente y cia', 'jayish', 'jeju beer co.', 'jesus carlos fantelli e hijos', 'joaquim thomaz de aquino filho', 'john martin', 'jovi', 'kabrew', 'kaos', 'karlsberg', 'katlenburger', 'kelterei heil', 'kelterei hohl', 'kelterei possmann', 'kelterei rapps', 'kirin', 'knr korea', 'kobe', 'kompania piwowarsk', 'kopparberg', 'krombacher', 'kwv', 'la brasserie mcausla', 'la farruca', 'la martiniquaise', 'la voie maltee', 'lakes', 'las perdices', 'le brun', 'le mule drinks la la drinks', 'lemon life', 'les brasseurs du nor', 'lexington brewing', 'liqs', 'll bebidas', 'lonetree', 'lost coast', 'lotte', 'lotteasahijuryu imp', 'loverboy', 'lowlander', 'loyal 9', 'lucas bols', 'luigi bosca', 'lusaka sla', 'lvmh', 'mahou_sanmiquel_ brw', 'maison des futailles', 'mamitas', 'mark anthony', 'markers edge', 'matt & steves', 'matthias stoeger', 'max wilhelm', 'mecklenburger', 'meens', 'megasuper', 'micro brewery korea', 'mighty swell', 'miks', 'minhas creek brewery', 'minoil', 'missiato', 'molinos rio de la plata', 'molson coors', 'mono azul', 'montebello', 'montucky', 'moortgat', 'moosehead breweries', 'mosquita muerta wines', 'moth drinks', 'mother earth', "mott's canada", 'mountauk', 'muhak imp', 'mule 2', 'muller', 'multidrink do brasil', 'muraro', 'muskoka cottge brwry', 'mybeer inc.', 'mz beverage imp', 'n/a', 'neobulles', 'new belgium', 'new glarus brewing', 'newage', 'niehoffs vaihinger', 'north coats brewing', 'northam group', 'northern monk brew', 'nova scotia spirit', 'nutreco', 'nuuv', 'oedipus', 'oettinger', 'ole', 'omer vander ghinste', 'ondrink', 'opal ltda', 'orchard city distilling', 'other manufacturers', 'otro loco', 'otros fabricantes', 'ovinto', 'pabst brewing', 'pacific western brewing company', 'palm', 'pamp brewing co', 'papy zouk', 'parallel 49', 'paramana ind e com de bebidas', 'paratudo', 'paris bebidas', 'partake brewing', 'paso pancho', 'passarin', 'patco', 'paulaner brewery', 'peer', 'pehuenia', 'pei brewing company', 'penaflor', 'penon del aguila', 'pernod ricard', 'peruanos', 'petropolis', 'pfriem', 'phillips brewing co', 'phusion projects', 'pinheirense', 'piracaia', 'pirassununga', 'pitu', 'platinum craft', 'porta', 'premier brand, ltd.', 'primo schincariol', 'privatbr eichbaum', 'private label', 'proximo', 'psicotella', 'pur vodka', 'putruele hnos', 'pyur', 'quash', 'que onda', 'quidi vidi brewery', 'quintessential brands', 'r.s.', 'rabieta', 'radeberger', 'rama caida', 'randon', 'real ale brewery', 'real canadian liquor store', 'refres now', 'refriko', 'refrix', 'regiane', 'regional trade', 'reino de castilla', 'remix', 'rewe', 'rhinegeist brewery', 'robert simpson', 'rothaus', 'rotkaeppchen', 'royal unibrew', 'rpb', 'russell brewing co', 'rutini', 'sabeco', 'sabores bolivianos alemanes', 'saenz briones', 'saint arnold brewing', 'salt point', 'salt spring apple', 'sambeb', 'san martino', 'sandbagger', 'sanmisangsa imp', 'santa filomena', 'santa rita', 'sapporo', 'sazerac', 'schneider weisse', 'schooner brewing', 'schwarze & schlichte', 'seven broi', 'shanghai bacchus', 'shepherd neame', 'shinsegae l&b imp', 'sidras mendocinas', 'sierra nevada', 'siri investments', 'sirsa', 'sleeman', 'snfood', 'so beer', 'sober carpenter', 'sociedad indl del sur', 'sociedad industrial del sur', 'sociedade de agro turismo quinta do ferro', 'sol ind.e com.de bebidas', 'sonoma', 'southern', 'spindrift', 'sqeeze brewery', 'squish', 'st. peter', 'stadacone distillery', 'stateside', 'statsbri wehnstphn', 'steam whistle brewin', 'stelz', 'stone brewing', 'sudamericana de bebidas', 'sun intl. imp', 'sunny delight', 'suntory', 'super bock group', 'sweetwater brewing', 'swinkels family brewers', 't & r theakston', 'taiama', 'tarnished distilling', 'tatuzinho 3 fazendas', 'teasy beverage', 'tequila cuervo la rojena', 'thatchers cider', 'the alcohol free co', 'the bombay', 'the boochery', 'the gambrinus', 'the long drink', 'the satellite brewing', 'thornbridge brewery', 'three floyds', 'three monkeys beer', 'three springs', 'tilray', 'tiny rebel brewing', 'toorank', 'tres leones', 'trivento bodegas y viñedos', 'troegs brewing', 'tron ice', 'tsingtao', 'tubito', 'tunuyan', 'twelve', 'underberg', 'united brands', 'united dutch breweries', 'upslope brewing', 'upstreet craft brwng', 'urban chestnut brewing', 'valentin bianchi', 'valle ballina & fernandez', 'van honsebrouck', 'van loveren', 'van pur', 'vancouver island', 'vanfall', 'vawter', 'veltins', 'verdi', 'verve', 'vetter', 'victoria distillers inc', 'vin de vin', 'vin up', 'vinhos duelo', 'vinhos quinta do nino', 'vinhos randon', 'vinicola aurora', 'vinicola girola', 'vinicola grassi', 'vocation brewery', 'warsteiner', 'welgreen radler', 'why brewery', 'william grant & sons', 'williams bros. brewing', 'worldbev', 'xeque mate bebidas', 'xyz', 'yvy destilaria', 'zing zang', 'zizi coin coin']`.
- **price_tier**: Must be one of `'core', 'core+', 'multiple', 'n/a', 'premium', 'super premium', 'tbc - opt', 'value'`.
- **price_tier_aggregated**: Must be one of `'core co', 'multiple', 'n/a', 'premium co'`.
- **style**: Must be selected from the exhaustive list: `['ale/ipa/pale ale/amber', 'beer - other', 'classic lager', 'coolers', 'flavored alcoholic beverages (fabs)', 'flavored non-alcoholic beer', 'flavoured beer', 'hard cider', 'hard seltzer', 'hard soda', 'highball', 'informal-millet brew', 'light lager/ easy drinking', 'multiple', 'n/a', 'non-alcoholic cider', 'non-alcoholic rtd', 'other beer', 'other ready to drink hard beverage (e.g. hard kombucha)', 'other rtd/ cider', 'other wines', 'radlers/beer mixes', 'ready-to-drink premixed cocktails/long drinks (alcoholic)', 'ready-to-drink premixed cocktails/long drinks without alcohol', 'red wine', 'rtd hard coffee', 'sparkling', 'spritzers', 'standard non-alcoholic beer', 'stout/dark beer', 'vodka', 'wheat/wit/weiss beer', 'white wine']`.
- **sub_brand**: Extracted brand names exactly as provided in query.
- **sub_category**: Must be selected from the exhaustive list: `['clear spirits', 'conventional beer', 'fabs, cooler, spritzers', 'flavoured beer', 'hard cider, perry', 'hard seltzer, soda', 'homebrew african beer', 'n/a', 'non-alcoholic beer', 'non-alcoholic cider', 'non-alcoholic rtd', 'other beer', 'other rtd/ cider', 'other wine', 'red wine', 'rtd - other', 'rtd cocktails', 'sparkling wine/ champagne', 'specialty beer', 'white wine', 'wine - others']`.
- **category**: Must be selected from the exhaustive list: `['beer', 'beer + bb', 'bottled water', 'carbonated softdrinks', 'energy drinks', 'formal + informal beer', 'formal + informal spirits', 'formal + informal wine', 'informal beer', 'informal spirits', 'informal wine', 'malts/local beverage', 'other alc drinks', 'other nab drinks', 'packaged juice', 'rtd cold coffee/tea', 'rtd/cider', 'spirits', 'sports drinks', 'wine']`.
- **analysis_level**: Must be explicitly one of `'direct'`, `'zone_aggregate'`, `'market_maturity_aggregate'`.
- **age, gender, income**: Cohort filters. If not mentioned, default to `'all'`.

---

## What will be implemented?
- Global Highlights for POS  (2025 Q4)


# Data ingestion roadmap

## What has been implemented?

This document buckets the ingested tables by **category analytics function** and, for each table, defines its role and gives **explicit examples of cuts and analyses** that can be retrieved.

---

### A) Core Category-Level KPIs

#### `POS_DIRECT_KPI_FACT`
**Role:** POS KPI fact table for category-level, macrocategory-level, brand-level, manufacturer-level, price tier level, price tier aggregated level, style level, sub-brand level and sub-category level.

**Primary keys and links:**
- `time_id` → `TIME_DIM`
- `cohort_id` → `COHORT_DIM`

**Attributes:** `country`, `brand`, `sub_brand`, `category`, `sub_category`, `price_tier`, `manufacturer`, `style`, `macrocategory`, `price_tier_aggregated`, `raw_category`, `market_maturity`

**Measures:**
`participation`, `occasions`, `servings`

**Example cuts and analyses:**
- **Time trend:** Participation of *Beer* in *Mexico* by quarter for *2023–2025* using `TIME_DIM.period='Q1'..'Q4'` and `TIME_DIM.year`.
- **Cohort slice:** Participation of *RTD/Cider* in *Brazil* for `COHORT_DIM.gender='female'`, `COHORT_DIM.age='18–24'`, `TIME_DIM.period='FY'`, `TIME_DIM.year='2024'`.
- **Manufacturer view:** *ABI* vs *Heineken* Participation in *Colombia*, `TIME_DIM.period='Q2'`, `TIME_DIM.year='2025'`.
- **Price segmentation:** Participation by *price_tier* (*Core*, *Premium*, *Super Premium*) for *Argentina*, `TIME_DIM.period='FY'`, `TIME_DIM.year='2024'`.
- **Macrocategory lens:** *Alcohol* vs *Non-Alcohol* Beverages share in *US*, `TIME_DIM.year='2023'..'2025'`.
- **Brand drilldown:** *Budweiser* vs *Corona* Participation and Servings in *UK*, `TIME_DIM.period='Q1'`, `TIME_DIM.year='2025'`.
- **Occasion mix:** Occasions distribution for *Beyond Beer* in *Canada*, split by `COHORT_DIM.income`.

---

### B) Market Maturity-Level Aggregates

#### `POS_MARKET_MATURITY_FACT`
**Role:** POS KPI fact table for Participation, Occasions, and Servings aggregated by market maturity segments (M1, M2, M3) with demographic breakdowns.

**Primary keys and links:**
- `time_id` → `TIME_DIM`
- `cohort_id` → `COHORT_DIM`

**Attributes:** `market_maturity`, `category`

**Measures:**
`participation`, `occasions`, `servings`

**Example cuts and analyses:**
- **Maturity view:** Participation across *M1*, *M2*, *M3* for *Beer* in `TIME_DIM.period='FY'`, `TIME_DIM.year='2024'`.
- **Cohort slice:** *Spirits* Participation for `market_maturity='M2'`, `COHORT_DIM.age='25–34'`, `TIME_DIM.period='FY'`, `TIME_DIM.year='2025'`.
- **Trend line:** Year-on-year change in *Beyond Beer* occasions in *M3* markets, `TIME_DIM.year='2023'..'2025'`.
- **Gender comparison:** Servings of *Wine* in *M1* by `COHORT_DIM.gender`.
- **Income split:** *Beer* Participation by `COHORT_DIM.income` in *M2* markets, `TIME_DIM.period='Q2'`, `TIME_DIM.year='2025'`.

---

### C) Zone-Level Aggregates

#### `POS_ZONE_KPI_FACT`
**Role:** POS KPI fact table for Participation, Occasions, and Servings aggregated at the zone level, with demographic breakdowns.

**Primary keys and links:**
- `time_id` → `TIME_DIM`
- `cohort_id` → `COHORT_DIM`

**Attributes:** `zone`, `category`

**Measures:**
`participation`, `occasions`, `servings`

**Example cuts and analyses:**
- **Zone lens:** Participation of *Beer* across *NAZ*, *SAZ*, *EUR*, *AFR*, *APAC*, `TIME_DIM.period='FY'`, `TIME_DIM.year='2024'`.
- **Cross-zone:** Compare *Beyond Beer* Participation in *APAC* vs *EUR* for `TIME_DIM.period='Q1'`, `TIME_DIM.year='2025'`.
- **Cohort slice:** *RTD/Cider* Participation in *SAZ* for `COHORT_DIM.age='18–24'`.
- **Occasion view:** *Wine* occasions by zone, `TIME_DIM.year='2023'..'2025'`.
- **Income splits:** *Beer* Servings in *NAZ* split by `COHORT_DIM.income`.

---

### D) Dimensions and Reference Data

#### `TIME_DIM`
**Role:** Canonical calendar and periodization reference.

**Columns:**
`time_id`, `period_type`, `period`, `year`

**Example uses:**
- Construct quarterly trends (*Q1–Q4*) for *Beer* Participation, *2023–2025*.
- Build rolling windows using `period_type='R12M'` for *Spirits*.
- Align *FY* comparisons across years for *Beyond Beer*.

#### `COHORT_DIM`
**Role:** Demographic cohort reference for slicing.

**Columns:**
`cohort_id`, `age`, `gender`, `income`

**Example uses:**
- Gender split of *Beer* Participation in *US*, `TIME_DIM.period='FY'`, `TIME_DIM.year='2024'`.
- Age group comparison of *RTD/Cider* occasions in *Mexico*, `TIME_DIM.period='Q1'`, `TIME_DIM.year='2025'`.
- Income-tier contrast of *Wine* servings in *Brazil*, `TIME_DIM.period='FY'`, `TIME_DIM.year='2025'`.

---

## What will be implemented?
- The POS data refresh pipeline to be automated (2025 Q4).
