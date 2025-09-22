import asyncio
from catholic_mass_readings import USCCB


async def fetch_daily_material_object():
    all_text = {}
    async with USCCB() as usccb:
        mass = await usccb.get_today_mass()
        if not mass:
            raise SystemExit("No Mass found for today")
        all_text["Mass Title"] = mass.title
        for section in mass.sections:
            if section.header == "Reading 1" or section.header == "Gospel" or section.header == "Reading 2":
                for reading in section.readings:
                    all_text[section.header] = reading.text
    return all_text 
async def daily_keyword_fetch():
    keywords = {}
    async with USCCB() as usccb:
        mass = await usccb.get_today_mass()
        if not mass:
            raise SystemExit("No Mass found for today")
        for section in mass.sections:
            if section.header == "Reading 1" or section.header == "Gospel" or section.header == "Reading 2":
                wholeTitle = section.readings[0].title.lower()
                wordbyword = wholeTitle.split(" ")
                wordbyword = wordbyword[(len(wordbyword) -3):(len(wordbyword))]
                wordStringed = ''
                for word in wordbyword:
                    wordStringed = wordStringed + ' ' + word.lower()
                keywords[wordStringed.strip()] = section.header
    return keywords


async def main():
    #material = await fetch_daily_material_object()
    #if material:
    #    print(f"Today's Catholic Mass Readings:\n{material}")
    #else:
    #    print("Failed to fetch readings.")    
    print(await daily_keyword_fetch())

asyncio.run(main())