import httpx 
import json
import base64

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

class AIClient:
    @staticmethod
    async def get_product_data(image_bytes, user_text, api_key):
        url = "https://openrouter.ai/api/v1/chat/completions"
    
        # ТВОЕ ЗАДАНИЕ: Напиши здесь промпт, который заставит ИИ 
        # вернуть JSON с полями: brand, article, color, compound, type, sizes (массив)
        prompt = """
            Изучи приложенное фото товара и описание пользователя: "{user_text}".
            Твоя задача — извлечь данные для системы маркировки "Честный Знак".

            Верни ТОЛЬКО JSON с такой структурой:
            {{
            "brand": "Название бренда (если нет, пиши 'Без бренда')",
            "article": "Артикул товара",
            "type": "Вид товара (например: Брюки, Рубашка, Платье)",
            "color": "Основной цвет (приоритет данным из текста пользователя)",
            "compound": "Состав (например: 95% хлопок, 5% эластан, всегда приводи состав к такому формату)",
            "gender": "Пол (например: Мужской)",
            "sizes": [
                {{"value": "Размер (например: 42 или L)", "count": количество_штук}}
            ]
            }}

            Важно: 
            1. Если пользователь указывает несколько цветов для одного артикула, раздели их на разные объекты в массиве 'products'. Каждый объект должен содержать свои размеры, относящиеся именно к этому цвету.
            2. Не пиши никакого текста, кроме JSON.
            3. Если цвет в тексте не указан, определи его с фотографии пользователя
            4. Если в тексте нет упоминаний про пол, определи его сам по фото
            """ 

        base64_image = encode_image(image_bytes)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "google/gemini-2.0-flash-lite-001",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt.format(user_text=user_text)},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                return json.loads(result['choices'][0]['message']['content'])
            else:
                raise Exception(f"AI Error: {response.status_code}")