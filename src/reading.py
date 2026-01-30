import asyncio
from catholic_mass_readings import USCCB
from datetime import datetime, timedelta
import json


async def get_material(material_type, wordsPerSlide=5)->dict:
    returnObject = {}
    async with USCCB() as usccb:
        # Try today's mass first
        mass = await usccb.get_today_mass()
        
        # If no mass data for today, try yesterday (in case of timezone issues
        # or USCCB website updating early for the next day)
        if not mass:
            print("[reading] No mass data for today, trying yesterday...")
            yesterday = datetime.now() - timedelta(days=1)
            try:
                mass = await usccb.get_mass_from_date(yesterday)
            except Exception as e:
                print(f"[reading] Error fetching yesterday's mass: {e}")
        
        if not mass:
            print("[reading] No mass data available")
            return {"slides": [], "wordsPerSlide": wordsPerSlide}
        
        material = None
        title = None
        for section in mass.sections:
            # Support both "Reading 1" and "First Reading" formats
            if (section.header == material_type or 
                (material_type == "Reading 1" and section.header == "First Reading") or
                (material_type == "Reading 2" and section.header == "Second Reading")):
                if section.readings:
                    material = section.readings[0].text
                    title = section.readings[0]
                break
        
        if material and title:
            wordNum = 0
            curSlide = ""
            wordList = material.split()
            slides = []
            for word in wordList:
                if wordNum < wordsPerSlide:
                    curSlide += word + " "
                    wordNum += 1
                else:
                    slides.append(curSlide.strip())
                    curSlide = word + " "
                    wordNum = 1
            # Don't forget the last slide
            if curSlide.strip():
                slides.append(curSlide.strip())
            
            returnObject["title"] = str(title)
            returnObject["slides"] = slides
            returnObject["wordsPerSlide"] = wordsPerSlide
        else:
            returnObject["slides"] = []
            returnObject["wordsPerSlide"] = wordsPerSlide
        
        return returnObject

async def main():
    pass
if __name__ == "__main__":
    asyncio.run(main())
