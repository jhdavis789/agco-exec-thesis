"""Build data/basket.json — the master SKU list (~400 items) used as the
input for the live retailer fetch.

Each row carries:
  sku_id           stable id, kebab-case
  category         grocery | household | hpc | electronics
  subcategory      meat | produce | dairy | pantry | frozen | beverages |
                   paper | laundry | cleaning | trash | kitchen | pet |
                   otc | vitamins | personal_care | baby_feminine |
                   batteries_cables | apparel | homegoods
  canonical_name   human-readable
  normalization    per_lb | per_oz | per_fl_oz | per_ct | per_load |
                   per_sheet | per_each
  search_query     fed to retailer search adapters
"""
from __future__ import annotations
import json
from pathlib import Path

# Each tuple: (canonical_name, normalization, search_query)
# search_query defaults to canonical_name lowercased if empty.

GROCERY_MEAT = [
    ("Boneless Skinless Chicken Breast",       "per_lb", "boneless skinless chicken breast"),
    ("Bone-in Chicken Thighs",                 "per_lb", "bone-in chicken thighs"),
    ("Whole Chicken",                          "per_lb", "whole roaster chicken"),
    ("Ground Beef 80/20",                      "per_lb", "ground beef 80/20"),
    ("Ground Beef 93/7",                       "per_lb", "ground beef 93 7 lean"),
    ("Boneless Ribeye Steak",                  "per_lb", "boneless ribeye steak"),
    ("NY Strip Steak",                         "per_lb", "ny strip steak"),
    ("Top Sirloin Steak",                      "per_lb", "top sirloin steak"),
    ("Beef Tenderloin",                        "per_lb", "beef tenderloin"),
    ("Beef Brisket",                           "per_lb", "beef brisket"),
    ("Pork Chops Boneless",                    "per_lb", "boneless pork chops"),
    ("Pork Tenderloin",                        "per_lb", "pork tenderloin"),
    ("Pork Shoulder",                          "per_lb", "pork shoulder roast"),
    ("Bacon Thick Cut 1lb",                    "per_lb", "thick cut bacon"),
    ("Turkey Breast Boneless",                 "per_lb", "boneless turkey breast"),
    ("Ground Turkey 93/7",                     "per_lb", "ground turkey 93 7"),
    ("Atlantic Salmon Fillet",                 "per_lb", "atlantic salmon fillet"),
    ("Cod Fillet",                             "per_lb", "cod fillet"),
    ("Tilapia Fillet",                         "per_lb", "tilapia fillet frozen"),
    ("Shrimp 21-25 ct",                        "per_lb", "shrimp 21 25 raw frozen"),
    ("Tuna Steak",                             "per_lb", "ahi tuna steak"),
    ("Hot Dogs Beef 8 ct",                     "per_ct", "all beef hot dogs 8 count"),
    ("Italian Sausage Mild",                   "per_lb", "italian sausage mild"),
    ("Breakfast Sausage Links",                "per_lb", "breakfast sausage links"),
    ("Sliced Deli Ham",                        "per_lb", "sliced deli ham"),
    ("Sliced Deli Turkey",                     "per_lb", "sliced deli turkey"),
    ("Sliced Roast Beef",                      "per_lb", "sliced deli roast beef"),
    ("Lamb Loin Chops",                        "per_lb", "lamb loin chops"),
    ("Beef Stew Meat",                         "per_lb", "beef stew meat cubed"),
    ("Whole Pork Loin",                        "per_lb", "whole pork loin"),
    ("Boneless Chicken Thighs",                "per_lb", "boneless chicken thighs"),
    ("Chicken Wings",                          "per_lb", "chicken wings party"),
    ("Pork Ribs Baby Back",                    "per_lb", "baby back pork ribs"),
    ("Beef Chuck Roast",                       "per_lb", "beef chuck roast"),
    ("Cornish Game Hen",                       "per_lb", "cornish game hen"),
]

GROCERY_PRODUCE = [
    ("Bananas",                       "per_lb", "bananas"),
    ("Gala Apples",                   "per_lb", "gala apples"),
    ("Honeycrisp Apples",             "per_lb", "honeycrisp apples"),
    ("Granny Smith Apples",           "per_lb", "granny smith apples"),
    ("Navel Oranges",                 "per_lb", "navel oranges"),
    ("Strawberries 1lb",              "per_lb", "fresh strawberries 1 lb"),
    ("Blueberries 6oz",               "per_oz", "fresh blueberries 6 oz"),
    ("Red Seedless Grapes",           "per_lb", "red seedless grapes"),
    ("Romaine Lettuce Hearts",        "per_ct", "romaine lettuce hearts 3 pack"),
    ("Baby Spinach 5oz",              "per_oz", "baby spinach 5 oz"),
    ("Broccoli Crowns",               "per_lb", "broccoli crowns fresh"),
    ("Baby Carrots 1lb",              "per_lb", "baby carrots 1 lb"),
    ("Russet Potatoes 5lb",           "per_lb", "russet potatoes 5 lb"),
    ("Sweet Potatoes",                "per_lb", "sweet potatoes"),
    ("Yellow Onions 3lb",             "per_lb", "yellow onions 3 lb bag"),
    ("Roma Tomatoes",                 "per_lb", "roma tomatoes"),
    ("Tomatoes On the Vine",          "per_lb", "tomatoes on the vine"),
    ("English Cucumbers",             "per_ct", "english cucumber"),
    ("Green Bell Peppers",            "per_ct", "green bell pepper"),
    ("Hass Avocados",                 "per_ct", "hass avocado"),
    ("Lemons",                        "per_ct", "lemon fresh"),
    ("Limes",                         "per_ct", "lime fresh"),
    ("White Mushrooms 8oz",           "per_oz", "white mushrooms 8 oz"),
    ("Garlic Bulbs",                  "per_ct", "garlic bulb"),
    ("Ginger Root",                   "per_lb", "ginger root"),
    ("Celery Hearts",                 "per_ct", "celery hearts"),
    ("Cauliflower Head",              "per_ct", "cauliflower head fresh"),
    ("Zucchini",                      "per_lb", "zucchini squash"),
    ("Yellow Squash",                 "per_lb", "yellow squash"),
    ("Iceberg Lettuce",               "per_ct", "iceberg lettuce head"),
]

GROCERY_DAIRY_EGGS = [
    ("Whole Milk Gallon",             "per_fl_oz", "whole milk 1 gallon"),
    ("2% Milk Gallon",                "per_fl_oz", "2 percent milk 1 gallon"),
    ("Skim Milk Gallon",              "per_fl_oz", "skim milk 1 gallon"),
    ("Half and Half Quart",           "per_fl_oz", "half and half quart"),
    ("Heavy Cream Pint",              "per_fl_oz", "heavy cream pint"),
    ("Large Eggs Dozen",              "per_ct", "large eggs dozen grade a"),
    ("Extra Large Eggs Dozen",        "per_ct", "extra large eggs dozen"),
    ("Cage Free Eggs Dozen",          "per_ct", "cage free eggs dozen"),
    ("Organic Eggs Dozen",            "per_ct", "organic eggs dozen"),
    ("Unsalted Butter 1lb",           "per_lb", "unsalted butter 1 lb"),
    ("Salted Butter 1lb",             "per_lb", "salted butter 1 lb"),
    ("American Cheese Singles 24ct",  "per_ct", "american cheese singles 24 count"),
    ("Sharp Cheddar Block 8oz",       "per_oz", "sharp cheddar cheese block 8 oz"),
    ("Mozzarella Shredded 8oz",       "per_oz", "shredded mozzarella 8 oz"),
    ("Parmesan Grated 8oz",           "per_oz", "grated parmesan 8 oz"),
    ("Greek Yogurt Plain 32oz",       "per_oz", "greek yogurt plain 32 oz"),
    ("Greek Yogurt Vanilla 32oz",     "per_oz", "greek yogurt vanilla 32 oz"),
    ("Sour Cream 16oz",               "per_oz", "sour cream 16 oz"),
    ("Cream Cheese 8oz",              "per_oz", "cream cheese block 8 oz philadelphia"),
    ("Cottage Cheese 16oz",           "per_oz", "cottage cheese 16 oz"),
    ("String Cheese 12ct",            "per_ct", "mozzarella string cheese 12 count"),
    ("Whipped Cream Aerosol 7oz",     "per_oz", "whipped cream aerosol 7 oz"),
    ("Almond Milk Half Gallon",       "per_fl_oz", "almond milk half gallon unsweetened"),
    ("Oat Milk Half Gallon",          "per_fl_oz", "oat milk half gallon"),
    ("Orange Juice 59oz",             "per_fl_oz", "orange juice 59 oz no pulp"),
]

GROCERY_PANTRY = [
    ("White Rice 5lb",                "per_lb", "long grain white rice 5 lb"),
    ("Brown Rice 5lb",                "per_lb", "brown rice 5 lb"),
    ("Jasmine Rice 5lb",              "per_lb", "jasmine rice 5 lb"),
    ("Spaghetti 1lb",                 "per_lb", "spaghetti pasta 1 lb"),
    ("Penne Pasta 1lb",               "per_lb", "penne pasta 1 lb"),
    ("Macaroni 1lb",                  "per_lb", "elbow macaroni 1 lb"),
    ("Marinara Sauce 24oz",           "per_oz", "marinara pasta sauce 24 oz"),
    ("Alfredo Sauce 15oz",            "per_oz", "alfredo pasta sauce 15 oz"),
    ("Peanut Butter Creamy 16oz",     "per_oz", "peanut butter creamy 16 oz jif"),
    ("Strawberry Jam 18oz",           "per_oz", "strawberry jam 18 oz smucker"),
    ("White Bread Loaf",              "per_oz", "white bread loaf 20 oz"),
    ("Whole Wheat Bread Loaf",        "per_oz", "whole wheat bread loaf 24 oz"),
    ("Cheerios Cereal 18oz",          "per_oz", "cheerios cereal 18 oz"),
    ("Frosted Flakes Cereal 24oz",    "per_oz", "frosted flakes cereal 24 oz"),
    ("Honey Nut Cheerios 18oz",       "per_oz", "honey nut cheerios 18 oz"),
    ("Old Fashioned Oats 42oz",       "per_oz", "old fashioned oats 42 oz quaker"),
    ("All Purpose Flour 5lb",         "per_lb", "all purpose flour 5 lb"),
    ("White Sugar 4lb",               "per_lb", "white granulated sugar 4 lb"),
    ("Brown Sugar 2lb",               "per_lb", "light brown sugar 2 lb"),
    ("Iodized Salt 26oz",             "per_oz", "iodized table salt 26 oz"),
    ("Extra Virgin Olive Oil 17oz",   "per_fl_oz", "extra virgin olive oil 17 oz"),
    ("Vegetable Oil 48oz",            "per_fl_oz", "vegetable oil 48 oz"),
    ("Canola Oil 48oz",               "per_fl_oz", "canola oil 48 oz"),
    ("Soy Sauce 10oz",                "per_fl_oz", "soy sauce 10 oz kikkoman"),
    ("Ketchup 32oz Heinz",            "per_oz", "heinz ketchup 32 oz"),
    ("Yellow Mustard 20oz",           "per_oz", "french's yellow mustard 20 oz"),
    ("Mayo 30oz Hellmann's",          "per_oz", "hellmann's mayo 30 oz"),
    ("Honey 12oz",                    "per_oz", "honey 12 oz bear"),
    ("Maple Syrup 12oz",              "per_fl_oz", "pure maple syrup 12 oz"),
    ("Chicken Broth 32oz",            "per_fl_oz", "chicken broth 32 oz"),
    ("Beef Broth 32oz",               "per_fl_oz", "beef broth 32 oz"),
    ("Diced Tomatoes 14.5oz",         "per_oz", "diced tomatoes 14.5 oz can"),
    ("Tomato Sauce 8oz",              "per_oz", "tomato sauce 8 oz can"),
    ("Black Beans 15oz Can",          "per_oz", "black beans 15 oz can"),
    ("Pinto Beans 15oz Can",          "per_oz", "pinto beans 15 oz can"),
    ("Tuna Chunk Light 5oz Can",      "per_oz", "chunk light tuna 5 oz can"),
    ("Salsa 16oz",                    "per_oz", "salsa medium 16 oz pace"),
    ("BBQ Sauce 18oz",                "per_oz", "bbq sauce 18 oz sweet baby ray"),
    ("Sriracha 17oz",                 "per_oz", "sriracha hot sauce 17 oz"),
    ("Hot Sauce Frank's 12oz",        "per_oz", "frank's red hot 12 oz"),
]

GROCERY_FROZEN = [
    ("Frozen Pepperoni Pizza 12in",   "per_oz", "frozen pepperoni pizza 12 inch"),
    ("Frozen Cheese Pizza 12in",      "per_oz", "frozen cheese pizza 12 inch"),
    ("Frozen Mixed Vegetables 12oz",  "per_oz", "frozen mixed vegetables 12 oz"),
    ("Frozen Broccoli 12oz",          "per_oz", "frozen broccoli florets 12 oz"),
    ("Frozen Corn 12oz",              "per_oz", "frozen corn 12 oz"),
    ("Frozen Peas 12oz",              "per_oz", "frozen peas 12 oz"),
    ("Vanilla Ice Cream 48oz",        "per_oz", "vanilla ice cream 48 oz"),
    ("Chocolate Ice Cream 48oz",      "per_oz", "chocolate ice cream 48 oz"),
    ("Frozen Waffles 10ct",           "per_ct", "eggo frozen waffles 10 count"),
    ("Frozen French Fries 32oz",      "per_oz", "frozen french fries 32 oz"),
    ("Frozen Tater Tots 32oz",        "per_oz", "frozen tater tots 32 oz"),
    ("Frozen Chicken Nuggets 32oz",   "per_oz", "frozen chicken nuggets 32 oz tyson"),
    ("Frozen Meatballs 32oz",         "per_oz", "frozen italian meatballs 32 oz"),
    ("Frozen Shrimp 1lb",             "per_lb", "frozen raw shrimp 1 lb"),
    ("Frozen Salmon Fillets 1lb",     "per_lb", "frozen salmon fillets 1 lb"),
    ("Frozen Strawberries 16oz",      "per_oz", "frozen strawberries 16 oz"),
    ("Frozen Blueberries 16oz",       "per_oz", "frozen blueberries 16 oz"),
    ("Frozen Lasagna 38oz",           "per_oz", "stouffer's frozen lasagna 38 oz"),
    ("Frozen Burritos 8ct",           "per_ct", "frozen bean and cheese burritos 8 count"),
    ("Hot Pockets 10ct",              "per_ct", "hot pockets 10 count"),
]

GROCERY_BEVERAGES = [
    ("Ground Coffee Folgers 30.5oz",  "per_oz", "folgers classic roast ground coffee 30.5 oz"),
    ("Whole Bean Coffee 12oz",        "per_oz", "starbucks whole bean coffee 12 oz pike place"),
    ("K-Cup Coffee Pods 24ct",        "per_ct", "keurig k cup coffee pods 24 count"),
    ("Black Tea Bags 100ct",          "per_ct", "lipton black tea bags 100 count"),
    ("Green Tea Bags 100ct",          "per_ct", "bigelow green tea bags 100 count"),
    ("Coke 12pk Cans",                "per_fl_oz", "coca cola 12 pack 12 oz cans"),
    ("Pepsi 12pk Cans",               "per_fl_oz", "pepsi 12 pack 12 oz cans"),
    ("Bottled Water 24pk",            "per_fl_oz", "bottled water 24 pack 16.9 oz"),
    ("Gatorade 8pk 20oz",             "per_fl_oz", "gatorade 8 pack 20 oz"),
    ("Apple Juice 64oz",              "per_fl_oz", "apple juice 64 oz mott's"),
]

HOUSEHOLD_PAPER = [
    ("Toilet Paper Charmin 12 Mega",  "per_sheet", "charmin ultra soft 12 mega rolls"),
    ("Toilet Paper Charmin 24 Mega",  "per_sheet", "charmin ultra soft 24 mega rolls"),
    ("Toilet Paper Cottonelle 12pk",  "per_sheet", "cottonelle ultra clean 12 mega rolls"),
    ("Toilet Paper Scott 1000 12pk",  "per_sheet", "scott 1000 12 rolls"),
    ("Bath Tissue Quilted Northern",  "per_sheet", "quilted northern ultra plush 12 mega rolls"),
    ("Paper Towels Bounty 6 Mega",    "per_sheet", "bounty paper towels 6 mega rolls"),
    ("Paper Towels Bounty 12 Mega",   "per_sheet", "bounty paper towels 12 mega rolls"),
    ("Paper Towels Brawny 8 Lg",      "per_sheet", "brawny paper towels 8 large rolls"),
    ("Paper Towels Sparkle 6 Lg",     "per_sheet", "sparkle paper towels 6 large rolls"),
    ("Paper Towels Viva 6 Lg",        "per_sheet", "viva paper towels 6 large rolls"),
    ("Facial Tissue Kleenex 3pk",     "per_ct", "kleenex facial tissue 3 pack 230 count"),
    ("Facial Tissue Puffs 8pk",       "per_ct", "puffs plus lotion 8 pack"),
    ("Napkins Dinner 200ct",          "per_ct", "vanity fair dinner napkins 200 count"),
    ("Paper Plates 100ct",            "per_ct", "dixie paper plates 10 inch 100 count"),
    ("Paper Bowls 100ct",             "per_ct", "dixie paper bowls 100 count"),
    ("Plastic Cups 16oz 100ct",       "per_ct", "solo red plastic cups 16 oz 100 count"),
    ("Plastic Forks 100ct",           "per_ct", "solo plastic forks 100 count"),
    ("Plastic Spoons 100ct",          "per_ct", "plastic spoons 100 count"),
    ("Disposable Wipes 75ct",         "per_ct", "disposable cleaning wipes 75 count"),
    ("Lunch Bags 50ct Brown",         "per_ct", "brown paper lunch bags 50 count"),
]

HOUSEHOLD_LAUNDRY = [
    ("Tide Original Liquid 92oz",     "per_load", "tide original liquid laundry detergent 92 oz"),
    ("Tide Pods 81ct",                "per_load", "tide pods original 81 count"),
    ("Gain Liquid 100oz",             "per_load", "gain original liquid detergent 100 oz"),
    ("Persil Liquid 100oz",           "per_load", "persil pro clean liquid 100 oz"),
    ("Arm and Hammer Liquid 144oz",   "per_load", "arm and hammer liquid detergent 144 oz"),
    ("All Free Clear Liquid 88oz",    "per_load", "all free and clear liquid 88 oz"),
    ("Downy Fabric Softener 103oz",   "per_load", "downy fabric softener 103 oz"),
    ("Bounce Dryer Sheets 240ct",     "per_ct", "bounce dryer sheets 240 count"),
    ("Snuggle Dryer Sheets 200ct",    "per_ct", "snuggle blue sparkle dryer sheets 200 count"),
    ("Clorox Bleach 121oz",           "per_fl_oz", "clorox regular bleach 121 oz"),
    ("OxiClean 7.22lb",               "per_lb", "oxiclean versatile stain remover 7.22 lb"),
    ("Shout Stain Remover 22oz",      "per_fl_oz", "shout stain remover 22 oz"),
    ("Color Catcher Sheets 72ct",     "per_ct", "shout color catcher 72 count"),
    ("Wool Dryer Balls 6ct",          "per_ct", "wool dryer balls 6 pack"),
    ("Stain Stick Tide 2.9oz",        "per_oz", "tide to go stain stick"),
]

HOUSEHOLD_CLEANING = [
    ("Clorox Wipes 75ct",             "per_ct", "clorox disinfecting wipes 75 count"),
    ("Lysol Wipes 80ct",              "per_ct", "lysol disinfecting wipes 80 count"),
    ("Lysol Spray 19oz",              "per_fl_oz", "lysol disinfectant spray 19 oz"),
    ("Dawn Dish Soap 28oz",           "per_fl_oz", "dawn ultra dish soap 28 oz"),
    ("Palmolive Dish Soap 32oz",      "per_fl_oz", "palmolive dish soap 32 oz"),
    ("Cascade Dishwasher Pods 60ct",  "per_ct", "cascade complete dishwasher pods 60 count"),
    ("Finish Dishwasher Pods 60ct",   "per_ct", "finish quantum dishwasher pods 60 count"),
    ("Glass Cleaner Windex 26oz",     "per_fl_oz", "windex glass cleaner 26 oz"),
    ("Mr Clean Multi Surface 40oz",   "per_fl_oz", "mr clean multi surface cleaner 40 oz"),
    ("Pine Sol 60oz",                 "per_fl_oz", "pine sol multi surface 60 oz"),
    ("Toilet Bowl Cleaner Lysol 24oz","per_fl_oz", "lysol toilet bowl cleaner 24 oz"),
    ("Bathroom Cleaner Scrubbing Bubbles","per_fl_oz", "scrubbing bubbles bathroom cleaner 32 oz"),
    ("Magic Eraser 8ct",              "per_ct", "mr clean magic eraser 8 count"),
    ("Sponges Scotch-Brite 9ct",      "per_ct", "scotch brite scrub sponges 9 count"),
    ("Microfiber Cloths 24ct",        "per_ct", "microfiber cleaning cloths 24 pack"),
]

HOUSEHOLD_TRASH = [
    ("Trash Bags 13gal Glad 110ct",   "per_ct", "glad forceflex 13 gallon 110 count"),
    ("Trash Bags 13gal Hefty 90ct",   "per_ct", "hefty 13 gallon 90 count"),
    ("Trash Bags 13gal Kirkland",     "per_ct", "kirkland signature 13 gallon"),
    ("Trash Bags 30gal 50ct",         "per_ct", "outdoor trash bags 30 gallon 50 count"),
    ("Trash Bags 33gal 50ct",         "per_ct", "trash bags 33 gallon 50 count"),
    ("Trash Bags 39gal Hefty 40ct",   "per_ct", "hefty strong 39 gallon 40 count"),
    ("Small Trash Bags 4gal 200ct",   "per_ct", "small trash bags 4 gallon 200 count"),
    ("Tall Kitchen Bags Drawstring",  "per_ct", "tall kitchen drawstring trash bags 80 count"),
    ("Compactor Bags 18gal 40ct",     "per_ct", "trash compactor bags 18 gallon 40 count"),
    ("Yard Waste Bags 30gal 5ct",     "per_ct", "yard waste paper bags 30 gallon 5 count"),
]

HOUSEHOLD_KITCHEN = [
    ("Ziploc Gallon 38ct",            "per_ct", "ziploc gallon freezer bags 38 count"),
    ("Ziploc Quart 75ct",             "per_ct", "ziploc quart freezer bags 75 count"),
    ("Ziploc Sandwich 145ct",         "per_ct", "ziploc sandwich bags 145 count"),
    ("Glad Cling Wrap 200sqft",       "per_sheet", "glad cling wrap 200 sq ft"),
    ("Reynolds Aluminum Foil 200ft",  "per_sheet", "reynolds wrap aluminum foil 200 sq ft"),
    ("Heavy Duty Foil 75sqft",        "per_sheet", "reynolds heavy duty foil 75 sq ft"),
    ("Parchment Paper 90sqft",        "per_sheet", "parchment paper 90 sq ft"),
    ("Wax Paper 75sqft",              "per_sheet", "wax paper 75 sq ft"),
    ("Disposable Containers 50ct",    "per_ct", "disposable food containers 50 count"),
    ("Coffee Filters 200ct",          "per_ct", "basket coffee filters 200 count"),
    ("Brita Filter 3pk",              "per_ct", "brita standard replacement filters 3 pack"),
    ("Dish Towels 8pk",               "per_ct", "kitchen dish towels 8 pack"),
    ("Oven Mitts 2pk",                "per_ct", "silicone oven mitts 2 pack"),
    ("Storage Containers 24pc",       "per_ct", "rubbermaid food storage 24 piece set"),
    ("Cookie Sheet Aluminum",         "per_each", "aluminum cookie baking sheet half"),
]

HOUSEHOLD_PET = [
    ("Purina Dog Chow 32lb",          "per_lb", "purina dog chow 32 lb"),
    ("Pedigree Dog Food 50lb",        "per_lb", "pedigree dog food 50 lb"),
    ("Blue Buffalo Dog Food 30lb",    "per_lb", "blue buffalo life protection dog 30 lb"),
    ("Iams Cat Food 16lb",            "per_lb", "iams proactive health cat 16 lb"),
    ("Friskies Cat Food 16lb",        "per_lb", "friskies surfin' turfin' cat 16 lb"),
    ("Tidy Cats Litter 35lb",         "per_lb", "tidy cats clumping litter 35 lb"),
    ("Fresh Step Cat Litter 25lb",    "per_lb", "fresh step clumping cat litter 25 lb"),
    ("Milkbone Dog Treats 24oz",      "per_oz", "milk bone dog treats 24 oz"),
    ("Greenies Dental Treats 27oz",   "per_oz", "greenies dental dog treats 27 oz"),
    ("Pup-peroni Dog Treats 22.5oz",  "per_oz", "pup peroni dog treats 22.5 oz"),
    ("Temptations Cat Treats 16oz",   "per_oz", "temptations cat treats 16 oz"),
    ("Wee Wee Pads 100ct",            "per_ct", "wee wee pads 100 count"),
    ("Dog Poop Bags 270ct",           "per_ct", "amazon basics dog waste bags 270 count"),
    ("Cat Food Cans 24pk",            "per_ct", "fancy feast cat food 24 pack 3 oz"),
    ("Wet Dog Food 12pk",             "per_ct", "pedigree wet dog food 12 pack"),
]

HPC_OTC = [
    ("Tylenol Extra Strength 100ct",  "per_ct", "tylenol extra strength 500 mg 100 count"),
    ("Advil 200ct",                   "per_ct", "advil ibuprofen 200 mg 200 count"),
    ("Motrin IB 100ct",               "per_ct", "motrin ib ibuprofen 100 count"),
    ("Aleve 100ct",                   "per_ct", "aleve naproxen 220 mg 100 count"),
    ("Bayer Aspirin 200ct",           "per_ct", "bayer aspirin 325 mg 200 count"),
    ("Claritin 30ct",                 "per_ct", "claritin loratadine 10 mg 30 count"),
    ("Zyrtec 45ct",                   "per_ct", "zyrtec cetirizine 10 mg 45 count"),
    ("Allegra 70ct",                  "per_ct", "allegra fexofenadine 180 mg 70 count"),
    ("Benadryl 100ct",                "per_ct", "benadryl diphenhydramine 25 mg 100 count"),
    ("DayQuil Severe 24ct",           "per_ct", "dayquil severe 24 count"),
    ("NyQuil Severe 24ct",            "per_ct", "nyquil severe 24 count"),
    ("Mucinex 12-Hour 40ct",          "per_ct", "mucinex 12 hour 40 count"),
    ("Robitussin DM 8oz",             "per_fl_oz", "robitussin dm 8 oz"),
    ("Pepto Bismol 16oz",             "per_fl_oz", "pepto bismol original 16 oz"),
    ("Tums Extra 96ct",               "per_ct", "tums extra strength 96 count"),
    ("Imodium 12ct",                  "per_ct", "imodium ad 12 count"),
    ("Prilosec OTC 42ct",             "per_ct", "prilosec otc 42 count"),
    ("Pepcid AC 50ct",                "per_ct", "pepcid ac 50 count"),
    ("Sudafed 24ct",                  "per_ct", "sudafed pe 24 count"),
    ("Halls Cough Drops 80ct",        "per_ct", "halls mentho lyptus 80 count"),
]

HPC_VITAMINS = [
    ("Centrum Adult 200ct",           "per_ct", "centrum adult multivitamin 200 count"),
    ("One A Day Men 200ct",           "per_ct", "one a day men's 200 count"),
    ("One A Day Women 200ct",         "per_ct", "one a day women's 200 count"),
    ("Vitamin C 1000mg 250ct",        "per_ct", "vitamin c 1000 mg 250 count"),
    ("Vitamin D3 5000IU 360ct",       "per_ct", "vitamin d3 5000 iu 360 count"),
    ("Fish Oil 1200mg 300ct",         "per_ct", "fish oil 1200 mg 300 count"),
    ("Melatonin 5mg 240ct",           "per_ct", "melatonin 5 mg 240 count"),
    ("Magnesium 500mg 250ct",         "per_ct", "magnesium 500 mg 250 count"),
    ("B12 1000mcg 200ct",             "per_ct", "vitamin b12 1000 mcg 200 count"),
    ("Biotin 5000mcg 200ct",          "per_ct", "biotin 5000 mcg 200 count"),
    ("Calcium 600mg 250ct",           "per_ct", "calcium 600 mg vitamin d 250 count"),
    ("Probiotics 60ct",               "per_ct", "probiotics 60 count"),
    ("Multivitamin Gummies 220ct",    "per_ct", "vitafusion multivitamin gummies 220 count"),
    ("Glucosamine Chondroitin 220ct", "per_ct", "glucosamine chondroitin 220 count"),
    ("Turmeric Curcumin 180ct",       "per_ct", "turmeric curcumin 180 count"),
    ("Apple Cider Vinegar Caps 90ct", "per_ct", "apple cider vinegar capsules 90 count"),
    ("Collagen Peptides 20oz",        "per_oz", "collagen peptides powder 20 oz"),
    ("Whey Protein 5lb",              "per_lb", "whey protein powder 5 lb"),
    ("Pre-Workout 30 servings",       "per_ct", "pre workout 30 servings"),
    ("Greens Powder 30 servings",     "per_ct", "greens powder 30 servings"),
]

HPC_PERSONAL_CARE = [
    ("Head Shoulders Shampoo 23.7oz", "per_fl_oz", "head and shoulders classic clean 23.7 oz"),
    ("Pantene Shampoo 25.4oz",        "per_fl_oz", "pantene pro v classic clean 25.4 oz"),
    ("Dove Conditioner 25.4oz",       "per_fl_oz", "dove daily moisture conditioner 25.4 oz"),
    ("Suave Conditioner 28oz",        "per_fl_oz", "suave conditioner 28 oz"),
    ("Dove Body Wash 22oz",           "per_fl_oz", "dove deep moisture body wash 22 oz"),
    ("Olay Body Wash 22oz",           "per_fl_oz", "olay ultra moisture body wash 22 oz"),
    ("Old Spice Body Wash 24oz",      "per_fl_oz", "old spice swagger body wash 24 oz"),
    ("Dial Bar Soap 8pk",             "per_ct", "dial gold bar soap 8 pack"),
    ("Irish Spring Bar Soap 8pk",     "per_ct", "irish spring original bar soap 8 pack"),
    ("Secret Deodorant 2.6oz",        "per_oz", "secret outlast deodorant 2.6 oz"),
    ("Old Spice Deodorant 3oz",       "per_oz", "old spice high endurance deodorant 3 oz"),
    ("Degree Deodorant 2.7oz",        "per_oz", "degree men's deodorant 2.7 oz"),
    ("Native Deodorant 2.65oz",       "per_oz", "native deodorant coconut vanilla 2.65 oz"),
    ("Colgate Toothpaste 6oz",        "per_oz", "colgate total whitening 6 oz"),
    ("Crest Toothpaste 5.7oz",        "per_oz", "crest 3d white toothpaste 5.7 oz"),
    ("Sensodyne Toothpaste 4oz",      "per_oz", "sensodyne pronamel 4 oz"),
    ("Listerine Mouthwash 1L",        "per_fl_oz", "listerine cool mint 1 liter"),
    ("Crest Mouthwash 1L",            "per_fl_oz", "crest pro health mouthwash 1 liter"),
    ("Oral-B Floss 3pk",              "per_ct", "oral b glide floss 3 pack"),
    ("Oral-B Toothbrushes 4pk",       "per_ct", "oral b crossaction toothbrush 4 pack"),
    ("Colgate Toothbrushes 6pk",      "per_ct", "colgate 360 toothbrush 6 pack"),
    ("Gillette Mach3 12pk",           "per_ct", "gillette mach 3 cartridges 12 pack"),
    ("Gillette Fusion 12pk",          "per_ct", "gillette fusion 5 cartridges 12 pack"),
    ("Schick Hydro Razors 12pk",      "per_ct", "schick hydro 5 cartridges 12 pack"),
    ("Shaving Cream Barbasol 10oz",   "per_oz", "barbasol shaving cream 10 oz"),
    ("Shaving Cream Gillette 11oz",   "per_oz", "gillette foamy shave cream 11 oz"),
    ("Cetaphil Lotion 20oz",          "per_fl_oz", "cetaphil moisturizing lotion 20 oz"),
    ("Aveeno Lotion 18oz",            "per_fl_oz", "aveeno daily moisturizing lotion 18 oz"),
    ("Vaseline 13oz",                 "per_fl_oz", "vaseline original 13 oz"),
    ("Q-Tips 750ct",                  "per_ct", "q tips cotton swabs 750 count"),
]

HPC_BABY_FEM = [
    ("Tampons Playtex Sport 36ct",    "per_ct", "playtex sport tampons 36 count"),
    ("Tampons Tampax Pearl 50ct",     "per_ct", "tampax pearl tampons 50 count"),
    ("Pads Always Ultra Thin 36ct",   "per_ct", "always ultra thin pads 36 count"),
    ("Pads Always Maxi 60ct",         "per_ct", "always maxi pads 60 count"),
    ("Liners Carefree 120ct",         "per_ct", "carefree pantiliners 120 count"),
    ("Diapers Huggies Sz 3 222ct",    "per_ct", "huggies little snugglers size 3 222 count"),
    ("Diapers Pampers Sz 3 168ct",    "per_ct", "pampers swaddlers size 3 168 count"),
    ("Diapers Luvs Sz 3 252ct",       "per_ct", "luvs size 3 252 count"),
    ("Diapers Huggies Sz 4 200ct",    "per_ct", "huggies snug and dry size 4 200 count"),
    ("Pull-Ups 4T-5T 56ct",           "per_ct", "pull ups training pants 4t 5t 56 count"),
    ("Baby Wipes Huggies 768ct",      "per_ct", "huggies natural care wipes 768 count"),
    ("Baby Wipes Pampers 720ct",      "per_ct", "pampers sensitive wipes 720 count"),
    ("Formula Similac Pro 36oz",      "per_oz", "similac pro advance 36 oz"),
    ("Formula Enfamil Neuropro 30oz", "per_oz", "enfamil neuropro 30 oz"),
    ("Baby Food Pouches 16pk",        "per_ct", "gerber baby food pouches 16 pack"),
    ("Diaper Rash Cream Desitin 4oz", "per_oz", "desitin diaper rash cream 4 oz"),
    ("Baby Lotion Johnson's 27oz",    "per_fl_oz", "johnsons baby lotion 27 oz"),
    ("Baby Shampoo Johnson's 27oz",   "per_fl_oz", "johnsons baby shampoo 27 oz"),
    ("Baby Powder Johnson's 22oz",    "per_oz", "johnsons baby powder 22 oz"),
    ("Pacifiers Philips 2pk",         "per_ct", "philips avent soothie pacifier 2 pack"),
]

ELECTRONICS = [
    ("AAA Alkaline Batteries 24pk Duracell", "per_ct", "duracell aaa batteries 24 pack"),
    ("AA Alkaline Batteries 24pk Duracell",  "per_ct", "duracell aa batteries 24 pack"),
    ("AAA Energizer 24pk",            "per_ct", "energizer max aaa 24 pack"),
    ("AA Energizer 24pk",             "per_ct", "energizer max aa 24 pack"),
    ("9V Batteries Duracell 4pk",     "per_ct", "duracell 9v batteries 4 pack"),
    ("CR2032 Coin 6pk",               "per_ct", "cr2032 coin batteries 6 pack"),
    ("HDMI Cable 6ft",                "per_each", "hdmi cable 6 ft 4k"),
    ("USB-C to USB-C Cable 6ft",      "per_each", "usb c to usb c cable 6 ft"),
    ("Lightning Cable 6ft",           "per_each", "apple lightning cable 6 ft"),
    ("USB-C Wall Charger 20W",        "per_each", "usb c wall charger 20w"),
    ("Power Strip 6 Outlet",          "per_each", "power strip surge protector 6 outlet"),
    ("Extension Cord 25ft",           "per_each", "extension cord 25 ft outdoor"),
    ("LED Bulb 60W Equiv 4pk",        "per_ct", "ge led 60w equivalent 4 pack"),
    ("LED Bulb Smart 4pk",            "per_ct", "philips hue white smart bulb 4 pack"),
    ("Echo Dot 5th Gen",              "per_each", "amazon echo dot 5th generation"),
    ("Roku Express 4K",               "per_each", "roku express 4k streaming device"),
    ("Apple AirPods 4",               "per_each", "apple airpods 4"),
    ("Samsung 65 4K TV",              "per_each", "samsung 65 inch 4k smart tv crystal"),
    ("Sony WH-CH520 Headphones",      "per_each", "sony wh ch520 wireless headphones"),
    ("Logitech MX Master 3S",         "per_each", "logitech mx master 3s wireless mouse"),
]

APPAREL = [
    ("Hanes Men's Crew Tee 6pk",      "per_ct", "hanes men's crew neck t shirt 6 pack white"),
    ("Hanes Men's Boxer Briefs 5pk",  "per_ct", "hanes men's boxer briefs 5 pack"),
    ("Hanes Women's Briefs 6pk",      "per_ct", "hanes women's cotton brief 6 pack"),
    ("Fruit of the Loom Socks 10pk",  "per_ct", "fruit of the loom men's socks 10 pack"),
    ("Hanes Women's Socks 10pk",      "per_ct", "hanes women's no show socks 10 pack"),
    ("Champion Hoodie Men's",         "per_each", "champion men's powerblend fleece hoodie"),
    ("Levi's 505 Jeans Men's",        "per_each", "levi's 505 men's jeans"),
    ("Carhartt Beanie",               "per_each", "carhartt acrylic watch hat beanie"),
    ("Crocs Classic Clogs",           "per_each", "crocs classic clog adult"),
    ("Hanes Men's Hoodie",            "per_each", "hanes men's ecosmart fleece hoodie"),
]

HOMEGOODS = [
    ("Bath Towel Set 4pk",            "per_ct", "cotton bath towels 4 pack"),
    ("Hand Towel Set 4pk",            "per_ct", "cotton hand towels 4 pack"),
    ("Washcloth Set 12pk",            "per_ct", "cotton washcloths 12 pack"),
    ("Sheet Set Twin",                "per_each", "twin sheet set 4 piece"),
    ("Sheet Set Queen",               "per_each", "queen sheet set 4 piece"),
    ("Pillow Standard 2pk",           "per_ct", "standard bed pillow 2 pack"),
    ("Comforter Queen",               "per_each", "queen comforter set"),
    ("Mattress Pad Queen",            "per_each", "queen mattress pad protector"),
    ("Throw Blanket Sherpa",          "per_each", "sherpa fleece throw blanket 50x60"),
    ("Memory Foam Mattress Topper Q", "per_each", "memory foam mattress topper queen"),
]


def assemble():
    sections = [
        ("grocery", "meat",            GROCERY_MEAT),
        ("grocery", "produce",         GROCERY_PRODUCE),
        ("grocery", "dairy_eggs",      GROCERY_DAIRY_EGGS),
        ("grocery", "pantry",          GROCERY_PANTRY),
        ("grocery", "frozen",          GROCERY_FROZEN),
        ("grocery", "beverages",       GROCERY_BEVERAGES),
        ("household", "paper",         HOUSEHOLD_PAPER),
        ("household", "laundry",       HOUSEHOLD_LAUNDRY),
        ("household", "cleaning",      HOUSEHOLD_CLEANING),
        ("household", "trash",         HOUSEHOLD_TRASH),
        ("household", "kitchen",       HOUSEHOLD_KITCHEN),
        ("household", "pet",           HOUSEHOLD_PET),
        ("hpc", "otc",                 HPC_OTC),
        ("hpc", "vitamins",            HPC_VITAMINS),
        ("hpc", "personal_care",       HPC_PERSONAL_CARE),
        ("hpc", "baby_feminine",       HPC_BABY_FEM),
        ("electronics", "batteries_cables", ELECTRONICS),
        ("electronics", "apparel",     APPAREL),
        ("electronics", "homegoods",   HOMEGOODS),
    ]

    skus = []
    counters = {}
    for category, subcategory, items in sections:
        for name, normalization, query in items:
            key = f"{category}-{subcategory}"
            counters[key] = counters.get(key, 0) + 1
            sku_id = f"{category}-{subcategory}-{counters[key]:03d}"
            skus.append({
                "sku_id": sku_id,
                "category": category,
                "subcategory": subcategory,
                "canonical_name": name,
                "normalization": normalization,
                "search_query": query,
            })
    return skus


def main():
    skus = assemble()
    out = {
        "generated_by": "scripts/build_basket.py",
        "target_zip": "30309",
        "n_skus": len(skus),
        "skus": skus,
    }
    path = Path(__file__).parent.parent / "data" / "basket.json"
    path.write_text(json.dumps(out, indent=2))
    by_cat = {}
    for s in skus:
        by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1
    print(f"wrote {path} with {len(skus)} skus")
    for c, n in by_cat.items():
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
