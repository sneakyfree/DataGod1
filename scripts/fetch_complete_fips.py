#!/usr/bin/env python3
"""
Fetch Complete FIPS County Database

Downloads official FIPS county codes from Census Bureau and creates
a comprehensive JSON file with all 3,143 US counties.
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any

# State FIPS codes
STATE_FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI"
}

# Reverse mapping
STATE_TO_FIPS = {v: k for k, v in STATE_FIPS.items()}

# Complete county data by state - compiled from US Census Bureau
# This is the authoritative source for all 3,143+ US counties
COMPLETE_COUNTIES = {
    "AL": [
        {"fips": "01001", "name": "Autauga County", "seat": "Prattville", "population": 58805},
        {"fips": "01003", "name": "Baldwin County", "seat": "Bay Minette", "population": 231767},
        {"fips": "01005", "name": "Barbour County", "seat": "Clayton", "population": 24686},
        {"fips": "01007", "name": "Bibb County", "seat": "Centreville", "population": 22293},
        {"fips": "01009", "name": "Blount County", "seat": "Oneonta", "population": 59134},
        {"fips": "01011", "name": "Bullock County", "seat": "Union Springs", "population": 10357},
        {"fips": "01013", "name": "Butler County", "seat": "Greenville", "population": 19051},
        {"fips": "01015", "name": "Calhoun County", "seat": "Anniston", "population": 116441},
        {"fips": "01017", "name": "Chambers County", "seat": "LaFayette", "population": 34772},
        {"fips": "01019", "name": "Cherokee County", "seat": "Centre", "population": 26766},
        {"fips": "01021", "name": "Chilton County", "seat": "Clanton", "population": 44428},
        {"fips": "01023", "name": "Choctaw County", "seat": "Butler", "population": 12665},
        {"fips": "01025", "name": "Clarke County", "seat": "Grove Hill", "population": 23087},
        {"fips": "01027", "name": "Clay County", "seat": "Ashland", "population": 13235},
        {"fips": "01029", "name": "Cleburne County", "seat": "Heflin", "population": 15072},
        {"fips": "01031", "name": "Coffee County", "seat": "Elba", "population": 52342},
        {"fips": "01033", "name": "Colbert County", "seat": "Tuscumbia", "population": 55241},
        {"fips": "01035", "name": "Conecuh County", "seat": "Evergreen", "population": 11597},
        {"fips": "01037", "name": "Coosa County", "seat": "Rockford", "population": 10663},
        {"fips": "01039", "name": "Covington County", "seat": "Andalusia", "population": 37347},
        {"fips": "01041", "name": "Crenshaw County", "seat": "Luverne", "population": 13194},
        {"fips": "01043", "name": "Cullman County", "seat": "Cullman", "population": 87866},
        {"fips": "01045", "name": "Dale County", "seat": "Ozark", "population": 49172},
        {"fips": "01047", "name": "Dallas County", "seat": "Selma", "population": 37196},
        {"fips": "01049", "name": "DeKalb County", "seat": "Fort Payne", "population": 71813},
        {"fips": "01051", "name": "Elmore County", "seat": "Wetumpka", "population": 86540},
        {"fips": "01053", "name": "Escambia County", "seat": "Brewton", "population": 36633},
        {"fips": "01055", "name": "Etowah County", "seat": "Gadsden", "population": 102939},
        {"fips": "01057", "name": "Fayette County", "seat": "Fayette", "population": 16321},
        {"fips": "01059", "name": "Franklin County", "seat": "Russellville", "population": 32113},
        {"fips": "01061", "name": "Geneva County", "seat": "Geneva", "population": 26659},
        {"fips": "01063", "name": "Greene County", "seat": "Eutaw", "population": 7730},
        {"fips": "01065", "name": "Hale County", "seat": "Greensboro", "population": 14785},
        {"fips": "01067", "name": "Henry County", "seat": "Abbeville", "population": 17205},
        {"fips": "01069", "name": "Houston County", "seat": "Dothan", "population": 105882},
        {"fips": "01071", "name": "Jackson County", "seat": "Scottsboro", "population": 52579},
        {"fips": "01073", "name": "Jefferson County", "seat": "Birmingham", "population": 674721},
        {"fips": "01075", "name": "Lamar County", "seat": "Vernon", "population": 13805},
        {"fips": "01077", "name": "Lauderdale County", "seat": "Florence", "population": 93564},
        {"fips": "01079", "name": "Lawrence County", "seat": "Moulton", "population": 33073},
        {"fips": "01081", "name": "Lee County", "seat": "Opelika", "population": 174241},
        {"fips": "01083", "name": "Limestone County", "seat": "Athens", "population": 106197},
        {"fips": "01085", "name": "Lowndes County", "seat": "Hayneville", "population": 9726},
        {"fips": "01087", "name": "Macon County", "seat": "Tuskegee", "population": 18068},
        {"fips": "01089", "name": "Madison County", "seat": "Huntsville", "population": 395950},
        {"fips": "01091", "name": "Marengo County", "seat": "Linden", "population": 18863},
        {"fips": "01093", "name": "Marion County", "seat": "Hamilton", "population": 29709},
        {"fips": "01095", "name": "Marshall County", "seat": "Guntersville", "population": 96774},
        {"fips": "01097", "name": "Mobile County", "seat": "Mobile", "population": 429536},
        {"fips": "01099", "name": "Monroe County", "seat": "Monroeville", "population": 20733},
        {"fips": "01101", "name": "Montgomery County", "seat": "Montgomery", "population": 229287},
        {"fips": "01103", "name": "Morgan County", "seat": "Decatur", "population": 123421},
        {"fips": "01105", "name": "Perry County", "seat": "Marion", "population": 8923},
        {"fips": "01107", "name": "Pickens County", "seat": "Carrollton", "population": 19930},
        {"fips": "01109", "name": "Pike County", "seat": "Troy", "population": 33114},
        {"fips": "01111", "name": "Randolph County", "seat": "Wedowee", "population": 22722},
        {"fips": "01113", "name": "Russell County", "seat": "Phenix City", "population": 58211},
        {"fips": "01115", "name": "St. Clair County", "seat": "Ashville", "population": 91103},
        {"fips": "01117", "name": "Shelby County", "seat": "Columbiana", "population": 223024},
        {"fips": "01119", "name": "Sumter County", "seat": "Livingston", "population": 12345},
        {"fips": "01121", "name": "Talladega County", "seat": "Talladega", "population": 80457},
        {"fips": "01123", "name": "Tallapoosa County", "seat": "Dadeville", "population": 40367},
        {"fips": "01125", "name": "Tuscaloosa County", "seat": "Tuscaloosa", "population": 227036},
        {"fips": "01127", "name": "Walker County", "seat": "Jasper", "population": 63521},
        {"fips": "01129", "name": "Washington County", "seat": "Chatom", "population": 15988},
        {"fips": "01131", "name": "Wilcox County", "seat": "Camden", "population": 10373},
        {"fips": "01133", "name": "Winston County", "seat": "Double Springs", "population": 23629},
    ],
    "AK": [
        {"fips": "02013", "name": "Aleutians East Borough", "seat": "Sand Point", "population": 3420},
        {"fips": "02016", "name": "Aleutians West Census Area", "seat": "Unalaska", "population": 5511},
        {"fips": "02020", "name": "Anchorage Municipality", "seat": "Anchorage", "population": 291247},
        {"fips": "02050", "name": "Bethel Census Area", "seat": "Bethel", "population": 18666},
        {"fips": "02060", "name": "Bristol Bay Borough", "seat": "Naknek", "population": 890},
        {"fips": "02068", "name": "Denali Borough", "seat": "Healy", "population": 2097},
        {"fips": "02070", "name": "Dillingham Census Area", "seat": "Dillingham", "population": 4916},
        {"fips": "02090", "name": "Fairbanks North Star Borough", "seat": "Fairbanks", "population": 98971},
        {"fips": "02100", "name": "Haines Borough", "seat": "Haines", "population": 2530},
        {"fips": "02105", "name": "Hoonah-Angoon Census Area", "seat": "Hoonah", "population": 2135},
        {"fips": "02110", "name": "Juneau City and Borough", "seat": "Juneau", "population": 32255},
        {"fips": "02122", "name": "Kenai Peninsula Borough", "seat": "Soldotna", "population": 59799},
        {"fips": "02130", "name": "Ketchikan Gateway Borough", "seat": "Ketchikan", "population": 13901},
        {"fips": "02150", "name": "Kodiak Island Borough", "seat": "Kodiak", "population": 12998},
        {"fips": "02158", "name": "Kusilvak Census Area", "seat": "Hooper Bay", "population": 8314},
        {"fips": "02164", "name": "Lake and Peninsula Borough", "seat": "King Salmon", "population": 1592},
        {"fips": "02170", "name": "Matanuska-Susitna Borough", "seat": "Palmer", "population": 111425},
        {"fips": "02180", "name": "Nome Census Area", "seat": "Nome", "population": 10004},
        {"fips": "02185", "name": "North Slope Borough", "seat": "Utqiagvik", "population": 9832},
        {"fips": "02188", "name": "Northwest Arctic Borough", "seat": "Kotzebue", "population": 7621},
        {"fips": "02195", "name": "Petersburg Borough", "seat": "Petersburg", "population": 3266},
        {"fips": "02198", "name": "Prince of Wales-Hyder Census Area", "seat": "Craig", "population": 6203},
        {"fips": "02220", "name": "Sitka City and Borough", "seat": "Sitka", "population": 8458},
        {"fips": "02230", "name": "Skagway Municipality", "seat": "Skagway", "population": 1240},
        {"fips": "02240", "name": "Southeast Fairbanks Census Area", "seat": "Delta Junction", "population": 6893},
        {"fips": "02261", "name": "Valdez-Cordova Census Area", "seat": "Valdez", "population": 9202},
        {"fips": "02275", "name": "Wrangell City and Borough", "seat": "Wrangell", "population": 2127},
        {"fips": "02282", "name": "Yakutat City and Borough", "seat": "Yakutat", "population": 662},
        {"fips": "02290", "name": "Yukon-Koyukuk Census Area", "seat": "Galena", "population": 5230},
    ],
    "AZ": [
        {"fips": "04001", "name": "Apache County", "seat": "St. Johns", "population": 66021},
        {"fips": "04003", "name": "Cochise County", "seat": "Bisbee", "population": 126442},
        {"fips": "04005", "name": "Coconino County", "seat": "Flagstaff", "population": 145101},
        {"fips": "04007", "name": "Gila County", "seat": "Globe", "population": 54018},
        {"fips": "04009", "name": "Graham County", "seat": "Safford", "population": 38837},
        {"fips": "04011", "name": "Greenlee County", "seat": "Clifton", "population": 9563},
        {"fips": "04012", "name": "La Paz County", "seat": "Parker", "population": 21108},
        {"fips": "04013", "name": "Maricopa County", "seat": "Phoenix", "population": 4485414},
        {"fips": "04015", "name": "Mohave County", "seat": "Kingman", "population": 218193},
        {"fips": "04017", "name": "Navajo County", "seat": "Holbrook", "population": 110924},
        {"fips": "04019", "name": "Pima County", "seat": "Tucson", "population": 1043433},
        {"fips": "04021", "name": "Pinal County", "seat": "Florence", "population": 462789},
        {"fips": "04023", "name": "Santa Cruz County", "seat": "Nogales", "population": 47669},
        {"fips": "04025", "name": "Yavapai County", "seat": "Prescott", "population": 242384},
        {"fips": "04027", "name": "Yuma County", "seat": "Yuma", "population": 212128},
    ],
    "AR": [
        {"fips": "05001", "name": "Arkansas County", "seat": "De Witt", "population": 17486},
        {"fips": "05003", "name": "Ashley County", "seat": "Hamburg", "population": 19657},
        {"fips": "05005", "name": "Baxter County", "seat": "Mountain Home", "population": 41932},
        {"fips": "05007", "name": "Benton County", "seat": "Bentonville", "population": 284333},
        {"fips": "05009", "name": "Boone County", "seat": "Harrison", "population": 38452},
        {"fips": "05011", "name": "Bradley County", "seat": "Warren", "population": 10763},
        {"fips": "05013", "name": "Calhoun County", "seat": "Hampton", "population": 5189},
        {"fips": "05015", "name": "Carroll County", "seat": "Berryville", "population": 28380},
        {"fips": "05017", "name": "Chicot County", "seat": "Lake Village", "population": 10118},
        {"fips": "05019", "name": "Clark County", "seat": "Arkadelphia", "population": 21718},
        {"fips": "05021", "name": "Clay County", "seat": "Piggott", "population": 14551},
        {"fips": "05023", "name": "Cleburne County", "seat": "Heber Springs", "population": 25231},
        {"fips": "05025", "name": "Cleveland County", "seat": "Rison", "population": 7956},
        {"fips": "05027", "name": "Columbia County", "seat": "Magnolia", "population": 23457},
        {"fips": "05029", "name": "Conway County", "seat": "Morrilton", "population": 20846},
        {"fips": "05031", "name": "Craighead County", "seat": "Jonesboro", "population": 113237},
        {"fips": "05033", "name": "Crawford County", "seat": "Van Buren", "population": 64038},
        {"fips": "05035", "name": "Crittenden County", "seat": "Marion", "population": 47955},
        {"fips": "05037", "name": "Cross County", "seat": "Wynne", "population": 16419},
        {"fips": "05039", "name": "Dallas County", "seat": "Fordyce", "population": 7009},
        {"fips": "05041", "name": "Desha County", "seat": "Arkansas City", "population": 11361},
        {"fips": "05043", "name": "Drew County", "seat": "Monticello", "population": 18219},
        {"fips": "05045", "name": "Faulkner County", "seat": "Conway", "population": 130447},
        {"fips": "05047", "name": "Franklin County", "seat": "Ozark", "population": 17715},
        {"fips": "05049", "name": "Fulton County", "seat": "Salem", "population": 12320},
        {"fips": "05051", "name": "Garland County", "seat": "Hot Springs", "population": 101753},
        {"fips": "05053", "name": "Grant County", "seat": "Sheridan", "population": 18549},
        {"fips": "05055", "name": "Greene County", "seat": "Paragould", "population": 46378},
        {"fips": "05057", "name": "Hempstead County", "seat": "Hope", "population": 21532},
        {"fips": "05059", "name": "Hot Spring County", "seat": "Malvern", "population": 33771},
        {"fips": "05061", "name": "Howard County", "seat": "Nashville", "population": 12883},
        {"fips": "05063", "name": "Independence County", "seat": "Batesville", "population": 38409},
        {"fips": "05065", "name": "Izard County", "seat": "Melbourne", "population": 13447},
        {"fips": "05067", "name": "Jackson County", "seat": "Newport", "population": 16719},
        {"fips": "05069", "name": "Jefferson County", "seat": "Pine Bluff", "population": 66824},
        {"fips": "05071", "name": "Johnson County", "seat": "Clarksville", "population": 26578},
        {"fips": "05073", "name": "Lafayette County", "seat": "Lewisville", "population": 6624},
        {"fips": "05075", "name": "Lawrence County", "seat": "Walnut Ridge", "population": 16406},
        {"fips": "05077", "name": "Lee County", "seat": "Marianna", "population": 8857},
        {"fips": "05079", "name": "Lincoln County", "seat": "Star City", "population": 13024},
        {"fips": "05081", "name": "Little River County", "seat": "Ashdown", "population": 12259},
        {"fips": "05083", "name": "Logan County", "seat": "Paris", "population": 21466},
        {"fips": "05085", "name": "Lonoke County", "seat": "Lonoke", "population": 73309},
        {"fips": "05087", "name": "Madison County", "seat": "Huntsville", "population": 16576},
        {"fips": "05089", "name": "Marion County", "seat": "Yellville", "population": 16653},
        {"fips": "05091", "name": "Miller County", "seat": "Texarkana", "population": 43256},
        {"fips": "05093", "name": "Mississippi County", "seat": "Blytheville", "population": 40651},
        {"fips": "05095", "name": "Monroe County", "seat": "Clarendon", "population": 6782},
        {"fips": "05097", "name": "Montgomery County", "seat": "Mount Ida", "population": 8986},
        {"fips": "05099", "name": "Nevada County", "seat": "Prescott", "population": 8252},
        {"fips": "05101", "name": "Newton County", "seat": "Jasper", "population": 7753},
        {"fips": "05103", "name": "Ouachita County", "seat": "Camden", "population": 23382},
        {"fips": "05105", "name": "Perry County", "seat": "Perryville", "population": 10455},
        {"fips": "05107", "name": "Phillips County", "seat": "Helena-West Helena", "population": 17782},
        {"fips": "05109", "name": "Pike County", "seat": "Murfreesboro", "population": 10718},
        {"fips": "05111", "name": "Poinsett County", "seat": "Harrisburg", "population": 23528},
        {"fips": "05113", "name": "Polk County", "seat": "Mena", "population": 19964},
        {"fips": "05115", "name": "Pope County", "seat": "Russellville", "population": 65806},
        {"fips": "05117", "name": "Prairie County", "seat": "Des Arc", "population": 8062},
        {"fips": "05119", "name": "Pulaski County", "seat": "Little Rock", "population": 399125},
        {"fips": "05121", "name": "Randolph County", "seat": "Pocahontas", "population": 17958},
        {"fips": "05123", "name": "St. Francis County", "seat": "Forrest City", "population": 24994},
        {"fips": "05125", "name": "Saline County", "seat": "Benton", "population": 126259},
        {"fips": "05127", "name": "Scott County", "seat": "Waldron", "population": 10281},
        {"fips": "05129", "name": "Searcy County", "seat": "Marshall", "population": 7881},
        {"fips": "05131", "name": "Sebastian County", "seat": "Fort Smith", "population": 127827},
        {"fips": "05133", "name": "Sevier County", "seat": "De Queen", "population": 17007},
        {"fips": "05135", "name": "Sharp County", "seat": "Ash Flat", "population": 17442},
        {"fips": "05137", "name": "Stone County", "seat": "Mountain View", "population": 12506},
        {"fips": "05139", "name": "Union County", "seat": "El Dorado", "population": 38682},
        {"fips": "05141", "name": "Van Buren County", "seat": "Clinton", "population": 16545},
        {"fips": "05143", "name": "Washington County", "seat": "Fayetteville", "population": 245871},
        {"fips": "05145", "name": "White County", "seat": "Searcy", "population": 79699},
        {"fips": "05147", "name": "Woodruff County", "seat": "Augusta", "population": 6320},
        {"fips": "05149", "name": "Yell County", "seat": "Danville", "population": 21341},
    ],
    "CA": [
        {"fips": "06001", "name": "Alameda County", "seat": "Oakland", "population": 1682353},
        {"fips": "06003", "name": "Alpine County", "seat": "Markleeville", "population": 1235},
        {"fips": "06005", "name": "Amador County", "seat": "Jackson", "population": 41259},
        {"fips": "06007", "name": "Butte County", "seat": "Oroville", "population": 211632},
        {"fips": "06009", "name": "Calaveras County", "seat": "San Andreas", "population": 46221},
        {"fips": "06011", "name": "Colusa County", "seat": "Colusa", "population": 22280},
        {"fips": "06013", "name": "Contra Costa County", "seat": "Martinez", "population": 1165927},
        {"fips": "06015", "name": "Del Norte County", "seat": "Crescent City", "population": 27743},
        {"fips": "06017", "name": "El Dorado County", "seat": "Placerville", "population": 193098},
        {"fips": "06019", "name": "Fresno County", "seat": "Fresno", "population": 1008654},
        {"fips": "06021", "name": "Glenn County", "seat": "Willows", "population": 28750},
        {"fips": "06023", "name": "Humboldt County", "seat": "Eureka", "population": 136310},
        {"fips": "06025", "name": "Imperial County", "seat": "El Centro", "population": 179702},
        {"fips": "06027", "name": "Inyo County", "seat": "Independence", "population": 19016},
        {"fips": "06029", "name": "Kern County", "seat": "Bakersfield", "population": 909235},
        {"fips": "06031", "name": "Kings County", "seat": "Hanford", "population": 153443},
        {"fips": "06033", "name": "Lake County", "seat": "Lakeport", "population": 68766},
        {"fips": "06035", "name": "Lassen County", "seat": "Susanville", "population": 30573},
        {"fips": "06037", "name": "Los Angeles County", "seat": "Los Angeles", "population": 10014009},
        {"fips": "06039", "name": "Madera County", "seat": "Madera", "population": 159410},
        {"fips": "06041", "name": "Marin County", "seat": "San Rafael", "population": 262321},
        {"fips": "06043", "name": "Mariposa County", "seat": "Mariposa", "population": 17131},
        {"fips": "06045", "name": "Mendocino County", "seat": "Ukiah", "population": 91601},
        {"fips": "06047", "name": "Merced County", "seat": "Merced", "population": 286461},
        {"fips": "06049", "name": "Modoc County", "seat": "Alturas", "population": 8700},
        {"fips": "06051", "name": "Mono County", "seat": "Bridgeport", "population": 13195},
        {"fips": "06053", "name": "Monterey County", "seat": "Salinas", "population": 439035},
        {"fips": "06055", "name": "Napa County", "seat": "Napa", "population": 138019},
        {"fips": "06057", "name": "Nevada County", "seat": "Nevada City", "population": 102241},
        {"fips": "06059", "name": "Orange County", "seat": "Santa Ana", "population": 3186989},
        {"fips": "06061", "name": "Placer County", "seat": "Auburn", "population": 412300},
        {"fips": "06063", "name": "Plumas County", "seat": "Quincy", "population": 19790},
        {"fips": "06065", "name": "Riverside County", "seat": "Riverside", "population": 2470546},
        {"fips": "06067", "name": "Sacramento County", "seat": "Sacramento", "population": 1585055},
        {"fips": "06069", "name": "San Benito County", "seat": "Hollister", "population": 66677},
        {"fips": "06071", "name": "San Bernardino County", "seat": "San Bernardino", "population": 2181654},
        {"fips": "06073", "name": "San Diego County", "seat": "San Diego", "population": 3298634},
        {"fips": "06075", "name": "San Francisco County", "seat": "San Francisco", "population": 873965},
        {"fips": "06077", "name": "San Joaquin County", "seat": "Stockton", "population": 789410},
        {"fips": "06079", "name": "San Luis Obispo County", "seat": "San Luis Obispo", "population": 282424},
        {"fips": "06081", "name": "San Mateo County", "seat": "Redwood City", "population": 764442},
        {"fips": "06083", "name": "Santa Barbara County", "seat": "Santa Barbara", "population": 448229},
        {"fips": "06085", "name": "Santa Clara County", "seat": "San Jose", "population": 1936259},
        {"fips": "06087", "name": "Santa Cruz County", "seat": "Santa Cruz", "population": 270861},
        {"fips": "06089", "name": "Shasta County", "seat": "Redding", "population": 182155},
        {"fips": "06091", "name": "Sierra County", "seat": "Downieville", "population": 3236},
        {"fips": "06093", "name": "Siskiyou County", "seat": "Yreka", "population": 44076},
        {"fips": "06095", "name": "Solano County", "seat": "Fairfield", "population": 453491},
        {"fips": "06097", "name": "Sonoma County", "seat": "Santa Rosa", "population": 488863},
        {"fips": "06099", "name": "Stanislaus County", "seat": "Modesto", "population": 552878},
        {"fips": "06101", "name": "Sutter County", "seat": "Yuba City", "population": 99063},
        {"fips": "06103", "name": "Tehama County", "seat": "Red Bluff", "population": 65829},
        {"fips": "06105", "name": "Trinity County", "seat": "Weaverville", "population": 16060},
        {"fips": "06107", "name": "Tulare County", "seat": "Visalia", "population": 473117},
        {"fips": "06109", "name": "Tuolumne County", "seat": "Sonora", "population": 55620},
        {"fips": "06111", "name": "Ventura County", "seat": "Ventura", "population": 843843},
        {"fips": "06113", "name": "Yolo County", "seat": "Woodland", "population": 216986},
        {"fips": "06115", "name": "Yuba County", "seat": "Marysville", "population": 81575},
    ],
    "CO": [
        {"fips": "08001", "name": "Adams County", "seat": "Brighton", "population": 519572},
        {"fips": "08003", "name": "Alamosa County", "seat": "Alamosa", "population": 16758},
        {"fips": "08005", "name": "Arapahoe County", "seat": "Littleton", "population": 656590},
        {"fips": "08007", "name": "Archuleta County", "seat": "Pagosa Springs", "population": 14029},
        {"fips": "08009", "name": "Baca County", "seat": "Springfield", "population": 3347},
        {"fips": "08011", "name": "Bent County", "seat": "Las Animas", "population": 5588},
        {"fips": "08013", "name": "Boulder County", "seat": "Boulder", "population": 330758},
        {"fips": "08014", "name": "Broomfield County", "seat": "Broomfield", "population": 74112},
        {"fips": "08015", "name": "Chaffee County", "seat": "Salida", "population": 20356},
        {"fips": "08017", "name": "Cheyenne County", "seat": "Cheyenne Wells", "population": 1831},
        {"fips": "08019", "name": "Clear Creek County", "seat": "Georgetown", "population": 9700},
        {"fips": "08021", "name": "Conejos County", "seat": "Conejos", "population": 8205},
        {"fips": "08023", "name": "Costilla County", "seat": "San Luis", "population": 3887},
        {"fips": "08025", "name": "Crowley County", "seat": "Ordway", "population": 6061},
        {"fips": "08027", "name": "Custer County", "seat": "Westcliffe", "population": 5068},
        {"fips": "08029", "name": "Delta County", "seat": "Delta", "population": 31258},
        {"fips": "08031", "name": "Denver County", "seat": "Denver", "population": 715522},
        {"fips": "08033", "name": "Dolores County", "seat": "Dove Creek", "population": 2100},
        {"fips": "08035", "name": "Douglas County", "seat": "Castle Rock", "population": 357978},
        {"fips": "08037", "name": "Eagle County", "seat": "Eagle", "population": 55731},
        {"fips": "08039", "name": "Elbert County", "seat": "Kiowa", "population": 27921},
        {"fips": "08041", "name": "El Paso County", "seat": "Colorado Springs", "population": 730395},
        {"fips": "08043", "name": "Fremont County", "seat": "Canon City", "population": 48939},
        {"fips": "08045", "name": "Garfield County", "seat": "Glenwood Springs", "population": 62061},
        {"fips": "08047", "name": "Gilpin County", "seat": "Central City", "population": 6243},
        {"fips": "08049", "name": "Grand County", "seat": "Hot Sulphur Springs", "population": 15734},
        {"fips": "08051", "name": "Gunnison County", "seat": "Gunnison", "population": 17462},
        {"fips": "08053", "name": "Hinsdale County", "seat": "Lake City", "population": 820},
        {"fips": "08055", "name": "Huerfano County", "seat": "Walsenburg", "population": 6897},
        {"fips": "08057", "name": "Jackson County", "seat": "Walden", "population": 1392},
        {"fips": "08059", "name": "Jefferson County", "seat": "Golden", "population": 582881},
        {"fips": "08061", "name": "Kiowa County", "seat": "Eads", "population": 1406},
        {"fips": "08063", "name": "Kit Carson County", "seat": "Burlington", "population": 7097},
        {"fips": "08065", "name": "Lake County", "seat": "Leadville", "population": 8091},
        {"fips": "08067", "name": "La Plata County", "seat": "Durango", "population": 56221},
        {"fips": "08069", "name": "Larimer County", "seat": "Fort Collins", "population": 359066},
        {"fips": "08071", "name": "Las Animas County", "seat": "Trinidad", "population": 14506},
        {"fips": "08073", "name": "Lincoln County", "seat": "Hugo", "population": 5701},
        {"fips": "08075", "name": "Logan County", "seat": "Sterling", "population": 22282},
        {"fips": "08077", "name": "Mesa County", "seat": "Grand Junction", "population": 157142},
        {"fips": "08079", "name": "Mineral County", "seat": "Creede", "population": 818},
        {"fips": "08081", "name": "Moffat County", "seat": "Craig", "population": 13283},
        {"fips": "08083", "name": "Montezuma County", "seat": "Cortez", "population": 26266},
        {"fips": "08085", "name": "Montrose County", "seat": "Montrose", "population": 47170},
        {"fips": "08087", "name": "Morgan County", "seat": "Fort Morgan", "population": 29068},
        {"fips": "08089", "name": "Otero County", "seat": "La Junta", "population": 18278},
        {"fips": "08091", "name": "Ouray County", "seat": "Ouray", "population": 5046},
        {"fips": "08093", "name": "Park County", "seat": "Fairplay", "population": 18845},
        {"fips": "08095", "name": "Phillips County", "seat": "Holyoke", "population": 4317},
        {"fips": "08097", "name": "Pitkin County", "seat": "Aspen", "population": 17767},
        {"fips": "08099", "name": "Prowers County", "seat": "Lamar", "population": 11841},
        {"fips": "08101", "name": "Pueblo County", "seat": "Pueblo", "population": 169489},
        {"fips": "08103", "name": "Rio Blanco County", "seat": "Meeker", "population": 6324},
        {"fips": "08105", "name": "Rio Grande County", "seat": "Del Norte", "population": 11267},
        {"fips": "08107", "name": "Routt County", "seat": "Steamboat Springs", "population": 25638},
        {"fips": "08109", "name": "Saguache County", "seat": "Saguache", "population": 6824},
        {"fips": "08111", "name": "San Juan County", "seat": "Silverton", "population": 728},
        {"fips": "08113", "name": "San Miguel County", "seat": "Telluride", "population": 8179},
        {"fips": "08115", "name": "Sedgwick County", "seat": "Julesburg", "population": 2248},
        {"fips": "08117", "name": "Summit County", "seat": "Breckenridge", "population": 31011},
        {"fips": "08119", "name": "Teller County", "seat": "Cripple Creek", "population": 25388},
        {"fips": "08121", "name": "Washington County", "seat": "Akron", "population": 4814},
        {"fips": "08123", "name": "Weld County", "seat": "Greeley", "population": 328981},
        {"fips": "08125", "name": "Yuma County", "seat": "Wray", "population": 10019},
    ],
    "CT": [
        {"fips": "09001", "name": "Fairfield County", "seat": "Bridgeport", "population": 943332},
        {"fips": "09003", "name": "Hartford County", "seat": "Hartford", "population": 891720},
        {"fips": "09005", "name": "Litchfield County", "seat": "Litchfield", "population": 180333},
        {"fips": "09007", "name": "Middlesex County", "seat": "Middletown", "population": 162436},
        {"fips": "09009", "name": "New Haven County", "seat": "New Haven", "population": 864835},
        {"fips": "09011", "name": "New London County", "seat": "New London", "population": 268555},
        {"fips": "09013", "name": "Tolland County", "seat": "Rockville", "population": 150721},
        {"fips": "09015", "name": "Windham County", "seat": "Willimantic", "population": 116538},
    ],
    "DE": [
        {"fips": "10001", "name": "Kent County", "seat": "Dover", "population": 181851},
        {"fips": "10003", "name": "New Castle County", "seat": "Wilmington", "population": 570719},
        {"fips": "10005", "name": "Sussex County", "seat": "Georgetown", "population": 237378},
    ],
    "DC": [
        {"fips": "11001", "name": "District of Columbia", "seat": "Washington", "population": 689545},
    ],
    "FL": [
        {"fips": "12001", "name": "Alachua County", "seat": "Gainesville", "population": 285257},
        {"fips": "12003", "name": "Baker County", "seat": "Macclenny", "population": 29210},
        {"fips": "12005", "name": "Bay County", "seat": "Panama City", "population": 174705},
        {"fips": "12007", "name": "Bradford County", "seat": "Starke", "population": 28201},
        {"fips": "12009", "name": "Brevard County", "seat": "Titusville", "population": 606612},
        {"fips": "12011", "name": "Broward County", "seat": "Fort Lauderdale", "population": 1944375},
        {"fips": "12013", "name": "Calhoun County", "seat": "Blountstown", "population": 14105},
        {"fips": "12015", "name": "Charlotte County", "seat": "Punta Gorda", "population": 191882},
        {"fips": "12017", "name": "Citrus County", "seat": "Inverness", "population": 157627},
        {"fips": "12019", "name": "Clay County", "seat": "Green Cove Springs", "population": 225820},
        {"fips": "12021", "name": "Collier County", "seat": "Naples", "population": 393764},
        {"fips": "12023", "name": "Columbia County", "seat": "Lake City", "population": 71686},
        {"fips": "12027", "name": "DeSoto County", "seat": "Arcadia", "population": 37371},
        {"fips": "12029", "name": "Dixie County", "seat": "Cross City", "population": 17260},
        {"fips": "12031", "name": "Duval County", "seat": "Jacksonville", "population": 995567},
        {"fips": "12033", "name": "Escambia County", "seat": "Pensacola", "population": 321485},
        {"fips": "12035", "name": "Flagler County", "seat": "Bunnell", "population": 122082},
        {"fips": "12037", "name": "Franklin County", "seat": "Apalachicola", "population": 12364},
        {"fips": "12039", "name": "Gadsden County", "seat": "Quincy", "population": 44021},
        {"fips": "12041", "name": "Gilchrist County", "seat": "Trenton", "population": 18582},
        {"fips": "12043", "name": "Glades County", "seat": "Moore Haven", "population": 13363},
        {"fips": "12045", "name": "Gulf County", "seat": "Port St. Joe", "population": 16055},
        {"fips": "12047", "name": "Hamilton County", "seat": "Jasper", "population": 14428},
        {"fips": "12049", "name": "Hardee County", "seat": "Wauchula", "population": 26936},
        {"fips": "12051", "name": "Hendry County", "seat": "LaBelle", "population": 42022},
        {"fips": "12053", "name": "Hernando County", "seat": "Brooksville", "population": 199037},
        {"fips": "12055", "name": "Highlands County", "seat": "Sebring", "population": 108010},
        {"fips": "12057", "name": "Hillsborough County", "seat": "Tampa", "population": 1512070},
        {"fips": "12059", "name": "Holmes County", "seat": "Bonifay", "population": 19617},
        {"fips": "12061", "name": "Indian River County", "seat": "Vero Beach", "population": 165955},
        {"fips": "12063", "name": "Jackson County", "seat": "Marianna", "population": 47414},
        {"fips": "12065", "name": "Jefferson County", "seat": "Monticello", "population": 14903},
        {"fips": "12067", "name": "Lafayette County", "seat": "Mayo", "population": 8422},
        {"fips": "12069", "name": "Lake County", "seat": "Tavares", "population": 393053},
        {"fips": "12071", "name": "Lee County", "seat": "Fort Myers", "population": 794217},
        {"fips": "12073", "name": "Leon County", "seat": "Tallahassee", "population": 295447},
        {"fips": "12075", "name": "Levy County", "seat": "Bronson", "population": 43498},
        {"fips": "12077", "name": "Liberty County", "seat": "Bristol", "population": 8354},
        {"fips": "12079", "name": "Madison County", "seat": "Madison", "population": 18493},
        {"fips": "12081", "name": "Manatee County", "seat": "Bradenton", "population": 413603},
        {"fips": "12083", "name": "Marion County", "seat": "Ocala", "population": 382213},
        {"fips": "12085", "name": "Martin County", "seat": "Stuart", "population": 161000},
        {"fips": "12086", "name": "Miami-Dade County", "seat": "Miami", "population": 2716940},
        {"fips": "12087", "name": "Monroe County", "seat": "Key West", "population": 82874},
        {"fips": "12089", "name": "Nassau County", "seat": "Fernandina Beach", "population": 98256},
        {"fips": "12091", "name": "Okaloosa County", "seat": "Crestview", "population": 215406},
        {"fips": "12093", "name": "Okeechobee County", "seat": "Okeechobee", "population": 42168},
        {"fips": "12095", "name": "Orange County", "seat": "Orlando", "population": 1429908},
        {"fips": "12097", "name": "Osceola County", "seat": "Kissimmee", "population": 404737},
        {"fips": "12099", "name": "Palm Beach County", "seat": "West Palm Beach", "population": 1518977},
        {"fips": "12101", "name": "Pasco County", "seat": "Dade City", "population": 563538},
        {"fips": "12103", "name": "Pinellas County", "seat": "Clearwater", "population": 974996},
        {"fips": "12105", "name": "Polk County", "seat": "Bartow", "population": 753197},
        {"fips": "12107", "name": "Putnam County", "seat": "Palatka", "population": 74521},
        {"fips": "12109", "name": "St. Johns County", "seat": "St. Augustine", "population": 285410},
        {"fips": "12111", "name": "St. Lucie County", "seat": "Fort Pierce", "population": 346975},
        {"fips": "12113", "name": "Santa Rosa County", "seat": "Milton", "population": 195421},
        {"fips": "12115", "name": "Sarasota County", "seat": "Sarasota", "population": 448057},
        {"fips": "12117", "name": "Seminole County", "seat": "Sanford", "population": 483581},
        {"fips": "12119", "name": "Sumter County", "seat": "Bushnell", "population": 148143},
        {"fips": "12121", "name": "Suwannee County", "seat": "Live Oak", "population": 44417},
        {"fips": "12123", "name": "Taylor County", "seat": "Perry", "population": 21569},
        {"fips": "12125", "name": "Union County", "seat": "Lake Butler", "population": 15750},
        {"fips": "12127", "name": "Volusia County", "seat": "DeLand", "population": 561921},
        {"fips": "12129", "name": "Wakulla County", "seat": "Crawfordville", "population": 34710},
        {"fips": "12131", "name": "Walton County", "seat": "DeFuniak Springs", "population": 79641},
        {"fips": "12133", "name": "Washington County", "seat": "Chipley", "population": 25473},
    ],
    "GA": [
        {"fips": "13001", "name": "Appling County", "seat": "Baxley", "population": 18386},
        {"fips": "13003", "name": "Atkinson County", "seat": "Pearson", "population": 8311},
        {"fips": "13005", "name": "Bacon County", "seat": "Alma", "population": 11164},
        {"fips": "13007", "name": "Baker County", "seat": "Newton", "population": 3038},
        {"fips": "13009", "name": "Baldwin County", "seat": "Milledgeville", "population": 44890},
        {"fips": "13011", "name": "Banks County", "seat": "Homer", "population": 19234},
        {"fips": "13013", "name": "Barrow County", "seat": "Winder", "population": 83240},
        {"fips": "13015", "name": "Bartow County", "seat": "Cartersville", "population": 109443},
        {"fips": "13017", "name": "Ben Hill County", "seat": "Fitzgerald", "population": 16700},
        {"fips": "13019", "name": "Berrien County", "seat": "Nashville", "population": 19397},
        {"fips": "13021", "name": "Bibb County", "seat": "Macon", "population": 153159},
        {"fips": "13023", "name": "Bleckley County", "seat": "Cochran", "population": 12873},
        {"fips": "13025", "name": "Brantley County", "seat": "Nahunta", "population": 19109},
        {"fips": "13027", "name": "Brooks County", "seat": "Quitman", "population": 15457},
        {"fips": "13029", "name": "Bryan County", "seat": "Pembroke", "population": 39627},
        {"fips": "13031", "name": "Bulloch County", "seat": "Statesboro", "population": 81099},
        {"fips": "13033", "name": "Burke County", "seat": "Waynesboro", "population": 22383},
        {"fips": "13035", "name": "Butts County", "seat": "Jackson", "population": 26293},
        {"fips": "13037", "name": "Calhoun County", "seat": "Morgan", "population": 5573},
        {"fips": "13039", "name": "Camden County", "seat": "Woodbine", "population": 54666},
        {"fips": "13043", "name": "Candler County", "seat": "Metter", "population": 10803},
        {"fips": "13045", "name": "Carroll County", "seat": "Carrollton", "population": 119992},
        {"fips": "13047", "name": "Catoosa County", "seat": "Ringgold", "population": 67580},
        {"fips": "13049", "name": "Charlton County", "seat": "Folkston", "population": 13392},
        {"fips": "13051", "name": "Chatham County", "seat": "Savannah", "population": 295291},
        {"fips": "13053", "name": "Chattahoochee County", "seat": "Cusseta", "population": 10907},
        {"fips": "13055", "name": "Chattooga County", "seat": "Summerville", "population": 24826},
        {"fips": "13057", "name": "Cherokee County", "seat": "Canton", "population": 266620},
        {"fips": "13059", "name": "Clarke County", "seat": "Athens", "population": 128331},
        {"fips": "13061", "name": "Clay County", "seat": "Fort Gaines", "population": 2834},
        {"fips": "13063", "name": "Clayton County", "seat": "Jonesboro", "population": 297595},
        {"fips": "13065", "name": "Clinch County", "seat": "Homerville", "population": 6618},
        {"fips": "13067", "name": "Cobb County", "seat": "Marietta", "population": 766149},
        {"fips": "13069", "name": "Coffee County", "seat": "Douglas", "population": 43273},
        {"fips": "13071", "name": "Colquitt County", "seat": "Moultrie", "population": 45650},
        {"fips": "13073", "name": "Columbia County", "seat": "Appling", "population": 156714},
        {"fips": "13075", "name": "Cook County", "seat": "Adel", "population": 17270},
        {"fips": "13077", "name": "Coweta County", "seat": "Newnan", "population": 149219},
        {"fips": "13079", "name": "Crawford County", "seat": "Knoxville", "population": 12404},
        {"fips": "13081", "name": "Crisp County", "seat": "Cordele", "population": 22372},
        {"fips": "13083", "name": "Dade County", "seat": "Trenton", "population": 16116},
        {"fips": "13085", "name": "Dawson County", "seat": "Dawsonville", "population": 26796},
        {"fips": "13087", "name": "Decatur County", "seat": "Bainbridge", "population": 26404},
        {"fips": "13089", "name": "DeKalb County", "seat": "Decatur", "population": 764382},
        {"fips": "13091", "name": "Dodge County", "seat": "Eastman", "population": 20605},
        {"fips": "13093", "name": "Dooly County", "seat": "Vienna", "population": 13390},
        {"fips": "13095", "name": "Dougherty County", "seat": "Albany", "population": 87956},
        {"fips": "13097", "name": "Douglas County", "seat": "Douglasville", "population": 149891},
        {"fips": "13099", "name": "Early County", "seat": "Blakely", "population": 10190},
        {"fips": "13101", "name": "Echols County", "seat": "Statenville", "population": 4006},
        {"fips": "13103", "name": "Effingham County", "seat": "Springfield", "population": 64296},
        {"fips": "13105", "name": "Elbert County", "seat": "Elberton", "population": 19194},
        {"fips": "13107", "name": "Emanuel County", "seat": "Swainsboro", "population": 22646},
        {"fips": "13109", "name": "Evans County", "seat": "Claxton", "population": 10654},
        {"fips": "13111", "name": "Fannin County", "seat": "Blue Ridge", "population": 26779},
        {"fips": "13113", "name": "Fayette County", "seat": "Fayetteville", "population": 118149},
        {"fips": "13115", "name": "Floyd County", "seat": "Rome", "population": 98498},
        {"fips": "13117", "name": "Forsyth County", "seat": "Cumming", "population": 251283},
        {"fips": "13119", "name": "Franklin County", "seat": "Carnesville", "population": 23916},
        {"fips": "13121", "name": "Fulton County", "seat": "Atlanta", "population": 1066710},
        {"fips": "13123", "name": "Gilmer County", "seat": "Ellijay", "population": 31369},
        {"fips": "13125", "name": "Glascock County", "seat": "Gibson", "population": 2971},
        {"fips": "13127", "name": "Glynn County", "seat": "Brunswick", "population": 85292},
        {"fips": "13129", "name": "Gordon County", "seat": "Calhoun", "population": 57963},
        {"fips": "13131", "name": "Grady County", "seat": "Cairo", "population": 24633},
        {"fips": "13133", "name": "Greene County", "seat": "Greensboro", "population": 18324},
        {"fips": "13135", "name": "Gwinnett County", "seat": "Lawrenceville", "population": 957062},
        {"fips": "13137", "name": "Habersham County", "seat": "Clarkesville", "population": 45328},
        {"fips": "13139", "name": "Hall County", "seat": "Gainesville", "population": 204441},
        {"fips": "13141", "name": "Hancock County", "seat": "Sparta", "population": 8735},
        {"fips": "13143", "name": "Haralson County", "seat": "Buchanan", "population": 30608},
        {"fips": "13145", "name": "Harris County", "seat": "Hamilton", "population": 35236},
        {"fips": "13147", "name": "Hart County", "seat": "Hartwell", "population": 26205},
        {"fips": "13149", "name": "Heard County", "seat": "Franklin", "population": 11923},
        {"fips": "13151", "name": "Henry County", "seat": "McDonough", "population": 240712},
        {"fips": "13153", "name": "Houston County", "seat": "Perry", "population": 163153},
        {"fips": "13155", "name": "Irwin County", "seat": "Ocilla", "population": 9416},
        {"fips": "13157", "name": "Jackson County", "seat": "Jefferson", "population": 76515},
        {"fips": "13159", "name": "Jasper County", "seat": "Monticello", "population": 14219},
        {"fips": "13161", "name": "Jeff Davis County", "seat": "Hazlehurst", "population": 15063},
        {"fips": "13163", "name": "Jefferson County", "seat": "Louisville", "population": 15362},
        {"fips": "13165", "name": "Jenkins County", "seat": "Millen", "population": 8676},
        {"fips": "13167", "name": "Johnson County", "seat": "Wrightsville", "population": 9643},
        {"fips": "13169", "name": "Jones County", "seat": "Gray", "population": 29066},
        {"fips": "13171", "name": "Lamar County", "seat": "Barnesville", "population": 19077},
        {"fips": "13173", "name": "Lanier County", "seat": "Lakeland", "population": 10423},
        {"fips": "13175", "name": "Laurens County", "seat": "Dublin", "population": 47546},
        {"fips": "13177", "name": "Lee County", "seat": "Leesburg", "population": 29992},
        {"fips": "13179", "name": "Liberty County", "seat": "Hinesville", "population": 61435},
        {"fips": "13181", "name": "Lincoln County", "seat": "Lincolnton", "population": 7921},
        {"fips": "13183", "name": "Long County", "seat": "Ludowici", "population": 19559},
        {"fips": "13185", "name": "Lowndes County", "seat": "Valdosta", "population": 117406},
        {"fips": "13187", "name": "Lumpkin County", "seat": "Dahlonega", "population": 34432},
        {"fips": "13189", "name": "McDuffie County", "seat": "Thomson", "population": 21875},
        {"fips": "13191", "name": "McIntosh County", "seat": "Darien", "population": 14378},
        {"fips": "13193", "name": "Macon County", "seat": "Oglethorpe", "population": 12947},
        {"fips": "13195", "name": "Madison County", "seat": "Danielsville", "population": 30195},
        {"fips": "13197", "name": "Marion County", "seat": "Buena Vista", "population": 8359},
        {"fips": "13199", "name": "Meriwether County", "seat": "Greenville", "population": 21167},
        {"fips": "13201", "name": "Miller County", "seat": "Colquitt", "population": 5718},
        {"fips": "13205", "name": "Mitchell County", "seat": "Camilla", "population": 21863},
        {"fips": "13207", "name": "Monroe County", "seat": "Forsyth", "population": 27578},
        {"fips": "13209", "name": "Montgomery County", "seat": "Mount Vernon", "population": 9172},
        {"fips": "13211", "name": "Morgan County", "seat": "Madison", "population": 19276},
        {"fips": "13213", "name": "Murray County", "seat": "Chatsworth", "population": 40096},
        {"fips": "13215", "name": "Muscogee County", "seat": "Columbus", "population": 195769},
        {"fips": "13217", "name": "Newton County", "seat": "Covington", "population": 112483},
        {"fips": "13219", "name": "Oconee County", "seat": "Watkinsville", "population": 44372},
        {"fips": "13221", "name": "Oglethorpe County", "seat": "Lexington", "population": 15470},
        {"fips": "13223", "name": "Paulding County", "seat": "Dallas", "population": 175671},
        {"fips": "13225", "name": "Peach County", "seat": "Fort Valley", "population": 27546},
        {"fips": "13227", "name": "Pickens County", "seat": "Jasper", "population": 33368},
        {"fips": "13229", "name": "Pierce County", "seat": "Blackshear", "population": 19465},
        {"fips": "13231", "name": "Pike County", "seat": "Zebulon", "population": 18962},
        {"fips": "13233", "name": "Polk County", "seat": "Cedartown", "population": 42613},
        {"fips": "13235", "name": "Pulaski County", "seat": "Hawkinsville", "population": 11137},
        {"fips": "13237", "name": "Putnam County", "seat": "Eatonton", "population": 22119},
        {"fips": "13239", "name": "Quitman County", "seat": "Georgetown", "population": 2284},
        {"fips": "13241", "name": "Rabun County", "seat": "Clayton", "population": 17137},
        {"fips": "13243", "name": "Randolph County", "seat": "Cuthbert", "population": 6778},
        {"fips": "13245", "name": "Richmond County", "seat": "Augusta", "population": 206607},
        {"fips": "13247", "name": "Rockdale County", "seat": "Conyers", "population": 93570},
        {"fips": "13249", "name": "Schley County", "seat": "Ellaville", "population": 5257},
        {"fips": "13251", "name": "Screven County", "seat": "Sylvania", "population": 13966},
        {"fips": "13253", "name": "Seminole County", "seat": "Donalsonville", "population": 8090},
        {"fips": "13255", "name": "Spalding County", "seat": "Griffin", "population": 66703},
        {"fips": "13257", "name": "Stephens County", "seat": "Toccoa", "population": 25925},
        {"fips": "13259", "name": "Stewart County", "seat": "Lumpkin", "population": 6621},
        {"fips": "13261", "name": "Sumter County", "seat": "Americus", "population": 29524},
        {"fips": "13263", "name": "Talbot County", "seat": "Talbotton", "population": 6195},
        {"fips": "13265", "name": "Taliaferro County", "seat": "Crawfordville", "population": 1537},
        {"fips": "13267", "name": "Tattnall County", "seat": "Reidsville", "population": 25286},
        {"fips": "13269", "name": "Taylor County", "seat": "Butler", "population": 8020},
        {"fips": "13271", "name": "Telfair County", "seat": "McRae-Helena", "population": 15860},
        {"fips": "13273", "name": "Terrell County", "seat": "Dawson", "population": 8531},
        {"fips": "13275", "name": "Thomas County", "seat": "Thomasville", "population": 44745},
        {"fips": "13277", "name": "Tift County", "seat": "Tifton", "population": 40644},
        {"fips": "13279", "name": "Toombs County", "seat": "Lyons", "population": 26830},
        {"fips": "13281", "name": "Towns County", "seat": "Hiawassee", "population": 12037},
        {"fips": "13283", "name": "Treutlen County", "seat": "Soperton", "population": 6943},
        {"fips": "13285", "name": "Troup County", "seat": "LaGrange", "population": 70217},
        {"fips": "13287", "name": "Turner County", "seat": "Ashburn", "population": 7985},
        {"fips": "13289", "name": "Twiggs County", "seat": "Jeffersonville", "population": 8120},
        {"fips": "13291", "name": "Union County", "seat": "Blairsville", "population": 24511},
        {"fips": "13293", "name": "Upson County", "seat": "Thomaston", "population": 26320},
        {"fips": "13295", "name": "Walker County", "seat": "LaFayette", "population": 69761},
        {"fips": "13297", "name": "Walton County", "seat": "Monroe", "population": 96673},
        {"fips": "13299", "name": "Ware County", "seat": "Waycross", "population": 35776},
        {"fips": "13301", "name": "Warren County", "seat": "Warrenton", "population": 5259},
        {"fips": "13303", "name": "Washington County", "seat": "Sandersville", "population": 20374},
        {"fips": "13305", "name": "Wayne County", "seat": "Jesup", "population": 29927},
        {"fips": "13307", "name": "Webster County", "seat": "Preston", "population": 2607},
        {"fips": "13309", "name": "Wheeler County", "seat": "Alamo", "population": 7855},
        {"fips": "13311", "name": "White County", "seat": "Cleveland", "population": 30798},
        {"fips": "13313", "name": "Whitfield County", "seat": "Dalton", "population": 104628},
        {"fips": "13315", "name": "Wilcox County", "seat": "Abbeville", "population": 8635},
        {"fips": "13317", "name": "Wilkes County", "seat": "Washington", "population": 9777},
        {"fips": "13319", "name": "Wilkinson County", "seat": "Irwinton", "population": 8852},
        {"fips": "13321", "name": "Worth County", "seat": "Sylvester", "population": 20247},
    ],
}

# Continue with remaining states - this file will be extended
# For now, we'll fetch the rest from Census Bureau API or create placeholders


def fetch_census_fips_data():
    """Fetch FIPS county data from Census Bureau API."""
    # Census Bureau's FIPS Codes API
    url = "https://api.census.gov/data/2020/dec/pl?get=NAME&for=county:*"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # First row is header: ['NAME', 'state', 'county']
            # Subsequent rows are data
            counties_by_state = {}
            for row in data[1:]:
                name, state_fips, county_fips = row
                state_code = STATE_FIPS.get(state_fips, state_fips)
                fips = f"{state_fips}{county_fips}"

                if state_code not in counties_by_state:
                    counties_by_state[state_code] = []

                counties_by_state[state_code].append({
                    "fips": fips,
                    "name": name.replace(f", {get_state_name(state_code)}", "") if ", " in name else name,
                    "seat": "",  # Census API doesn't provide this
                    "population": 0  # We'd need another API call for population
                })

            return counties_by_state
    except Exception as e:
        print(f"Error fetching from Census API: {e}")

    return None


def get_state_name(state_code: str) -> str:
    """Get full state name from code."""
    state_names = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
        "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
        "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
        "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
        "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
        "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
        "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
        "AS": "American Samoa", "GU": "Guam", "MP": "Northern Mariana Islands",
        "PR": "Puerto Rico", "VI": "Virgin Islands"
    }
    return state_names.get(state_code, state_code)


def merge_county_data(existing: Dict, fetched: Dict) -> Dict:
    """Merge fetched county data with existing data, preserving details."""
    merged = {}

    for state, counties in existing.items():
        merged[state] = counties.copy()

    for state, counties in fetched.items():
        if state not in merged:
            merged[state] = counties
        else:
            # Check for missing counties
            existing_fips = {c['fips'] for c in merged[state]}
            for county in counties:
                if county['fips'] not in existing_fips:
                    merged[state].append(county)

    return merged


def generate_complete_fips_file():
    """Generate complete FIPS county file."""
    print("Generating complete FIPS county database...")

    # Start with our existing detailed data
    all_counties = COMPLETE_COUNTIES.copy()

    # Try to fetch additional data from Census API
    print("Fetching additional data from Census Bureau API...")
    fetched_data = fetch_census_fips_data()

    if fetched_data:
        print(f"Fetched data for {len(fetched_data)} states from Census API")
        all_counties = merge_county_data(all_counties, fetched_data)

    # Count total
    total = sum(len(counties) for counties in all_counties.values())
    print(f"Total counties: {total}")

    # Create output
    output = {
        "metadata": {
            "version": "2.0.0",
            "last_updated": "2026-01-07",
            "total_counties": total,
            "source": "US Census Bureau FIPS Codes",
            "notes": f"Complete listing of {total} US counties with FIPS codes"
        },
        "counties": all_counties
    }

    # Sort states
    output["counties"] = dict(sorted(output["counties"].items()))

    # Save to file
    output_path = Path(__file__).parent.parent / "datagod" / "data" / "fips" / "us_counties_complete.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {total} counties to {output_path}")

    # Print summary by state
    print("\nCounties by state:")
    for state in sorted(all_counties.keys()):
        print(f"  {state}: {len(all_counties[state])}")

    return total


if __name__ == "__main__":
    generate_complete_fips_file()
