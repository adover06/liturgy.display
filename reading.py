import asyncio
from catholic_mass_readings import USCCB
import json

async def fetch_daily_material_object():
    all_text = {}
    async with USCCB() as usccb:
        mass = await usccb.get_today_mass()
        if not mass:
            raise SystemExit("No Mass found for today")
        all_text["Mass Title"] = mass.title
        for section in mass.sections:
            if section.header == "Reading I" or section.header == "Gospel" or section.header == "Reading II":
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
            if section.header == "Reading I" or section.header == "Gospel" or section.header == "Reading II":
                for readings in section.readings:
                    keywords[" ".join(readings.text.split(" ")[:10]).lower()] = readings.text
    return keywords

async def get_material(material_type):
    material = ""
    async with USCCB() as usccb:
        mass = await usccb.get_today_mass()
        if not mass:
            return "SJSU Newman Center"
        for section in mass.sections:
            if section.header == material_type:
                print(section.readings[0].text)
                material = section.readings[0].text 
                return material
        return "SJSU Newman Center"

async def main():
    #print(await get_material("Reading 2"))
    # material = await fetch_daily_material_object()
    # if material:
    #    print(f"Today's Catholic Mass Readings:\n{json.dumps(material, indent=2)}")
    # else:
    #    print("Failed to fetch readings.")    
    # print(await daily_keyword_fetch())
    asyncio.run(main())