import asyncio
from catholic_mass_readings import USCCB
import json


async def get_material(material_type, wordsPerSlide=5)->dict:
    returnObject = {}
    async with USCCB() as usccb:
        mass = await usccb.get_today_mass()
        
        if not mass:
            return {"slides": [], "wordsPerSlide": wordsPerSlide}
        
        material = None
        title = None
        for section in mass.sections:
            if section.header == material_type:
                #print(section.readings[0].text)
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
