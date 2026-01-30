import json
import string
data = None
try:
    with open('model/nabre.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        if data is not None:
            print("NABRE JSON loaded successfully.")
except Exception as e:
    print(f"Error loading JSON: {e}")



try:  
    with open('model/words.txt', 'w') as file:
        for book in data:
                chapters = book["chapters"]
                for chapter in chapters:
                    versees = chapter["verses"]
                    for verse in versees:
                        verse_text = verse.get("text", "")
                        word_array = verse_text.split()
                        for word in word_array:
                            cleaned_word = word.translate(str.maketrans('', '', string.punctuation)).replace('\n', '').replace('\r', '').strip()
                            if cleaned_word:
                                file.write(cleaned_word + '\n')
except Exception as e:
    print(f"Error processing JSON data: {e}")
