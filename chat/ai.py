import torch
from llama_cpp import Llama
import logging
try:
    from .config import MODEL_PATH, AI_SETTINGS, get_system_prompt
except ImportError:
    from chat.config import MODEL_PATH, AI_SETTINGS, get_system_prompt

class AIModel:
    def __init__(self, custom_system_prompt: str = None):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False
        self.model_name = MODEL_PATH
        self.custom_system_prompt = custom_system_prompt  # Кастомный промпт для аккаунта
        
    def load_model(self):
        """Загружает модель и токенизатор"""
        try:
            self.logger.info("🤖 Загрузка")
            
            # Путь к вашему Q2_K файлу
            import os
            model_path = os.path.join(os.path.dirname(__file__), "model", "Roleplay-Llama-3-8B-Q5_K_M.gguf")
            
            if not os.path.exists(model_path):
                self.logger.error(f"❌ Файл модели не найден: {model_path}")
                return False
            
            # Определяем режим: CPU или GPU (если CUDA доступна)
            gpu_layers = 0
            if torch.cuda.is_available():
                # Стартовое значение: попытаться выгрузить все слои на GPU
                # llama.cpp сам ограничит по возможностям
                gpu_layers = 100
                try:
                    gpu_name = torch.cuda.get_device_name(0)
                except Exception:
                    gpu_name = "Unknown GPU"
                self.logger.info(f"⚙️ Обнаружен GPU: {gpu_name}. Включаю оффлоад слоёв (n_gpu_layers={gpu_layers}).")
            else:
                self.logger.info("⚙️ CUDA недоступна. Запускаю модель на CPU.")

            # Загружаем GGUF модель (GPU, если доступна)
            self.model = Llama(
                model_path=model_path,
                n_ctx=4096,  # Llama 3 RP обычно выгодно дать больше контекста
                n_threads=0,
                verbose=False,
                use_mmap=True,
                use_mlock=False,
                n_gpu_layers=gpu_layers,
                chat_format="llama-3",  # RP-билд под Llama 3
            )
            
            self.is_loaded = True
            if gpu_layers > 0:
                self.logger.info("✅ Модель загружена с оффлоадом на GPU")
            else:
                self.logger.info("✅ Модель загружена на CPU")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки модели: {e}")
            return False
    
    def _translate_to_russian(self, response: str) -> str:
        """Переводит ответ на русский язык, сохраняя контекст"""
        if not response or not response.strip():
            return response
            
        try:
            import re
            from deep_translator import GoogleTranslator
            
            # Проверяем, есть ли английские слова в тексте
            english_pattern = r'\b[a-zA-Z]{2,}\b'  # Минимум 2 буквы, чтобы не трогать союзы
            english_words = re.findall(english_pattern, response)
            
            # Если есть английские слова - переводим
            if english_words:
                translator = GoogleTranslator(source='auto', target='ru')
                
                # Разделяем текст на части: русские и английские
                parts = re.split(r'(\b[a-zA-Z\s]+\b)', response)
                translated_parts = []
                
                for part in parts:
                    if not part.strip():
                        translated_parts.append(part)
                        continue
                        
                    # Если часть содержит английские буквы - переводим
                    if re.search(r'[a-zA-Z]', part):
                        try:
                            translated = translator.translate(part.strip())
                            # Добавляем пробел перед переведенной частью, если нужно
                            if translated_parts and not translated_parts[-1].endswith(' '):
                                translated_parts.append(' ')
                            translated_parts.append(translated)
                        except Exception:
                            translated_parts.append(part)
                    else:
                        translated_parts.append(part)
                
                result = ''.join(translated_parts)
                # Убираем двойные пробелы
                result = re.sub(r'\s+', ' ', result).strip()
                return result
            
            return response  # Возвращаем оригинал, если нет английских слов
                    
        except Exception as e:
            self.logger.error(f"Ошибка перевода: {e}")
            return response
    
    def _format_prompt_with_context(self, prompt_template: str) -> str:
        """Подставляет динамические значения (время, активность, настроение) в промпт"""
        from datetime import datetime, timezone
        from bisect import bisect_right
        
        try:
            # Пытаемся использовать zoneinfo для МСК
            from zoneinfo import ZoneInfo
            msk_tz = ZoneInfo("Europe/Moscow")
            now = datetime.now(msk_tz)
            current_time_msk = now.strftime("%d.%m.%Y %H:%M")
        except Exception:
            # Fallback на UTC
            now = datetime.now(timezone.utc)
            current_time_msk = now.strftime("%d.%m.%Y %H:%M") + " UTC"
        
        hour = now.hour
        weekday = now.weekday()
        month = now.month
        
        # День недели
        weekdays_ru = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
        day_of_week = weekdays_ru[weekday]
        is_weekend = weekday >= 5
        
        # Сезон
        season = ("зима", "весна", "лето", "осень")[(month % 12) // 3]
        
        # Активность
        time_boundaries = (7, 10, 14, 18, 23)
        weekday_activities = (
            "спишь или очень поздно бодрствуешь",
            "просыпаешься и собираешься на работу/учебу",
            "на работе или учебе",
            "занят работой или учебой",
            "дома после работы, занимаешься своими делами",
            "спишь или очень поздно бодрствуешь",
        )
        weekend_activities = (
            "спишь или очень поздно бодрствуешь",
            "просыпаешься, неспеша собираешься",
            "отдыхаешь или занимаешься своими делами",
            "дома, можешь работать или просто отдыхать",
            "дома, занимаешься своими делами",
            "спишь или очень поздно бодрствуешь",
        )
        activities = weekend_activities if is_weekend else weekday_activities
        idx = bisect_right(time_boundaries, hour)
        current_activity = activities[idx]
        
        # Настроение
        if hour < 7 or hour >= 23:
            current_mood = "очень сонный" if hour < 3 else "засиделся, но уже поздно"
        elif hour < 10:
            current_mood = "немного сонный, но бодрый" if not is_weekend else "выспавшийся, расслабленный"
        elif hour < 14:
            current_mood = "активный, в работе или учёбе"
        elif hour < 18:
            current_mood = "уставший после учёбы, но ещё есть силы"
        else:
            current_mood = "расслабленный, отдыхаешь после дня"
        
        # Форматируем промпт
        return prompt_template.format(
            CURRENT_TIME_MSK=current_time_msk,
            DAY_OF_WEEK=day_of_week,
            CURRENT_ACTIVITY=current_activity,
            CURRENT_MOOD=current_mood,
            SEASON=season
        )
    
    def _finalize_response(self, text: str) -> str:
        """Приводит ответ к завершённому виду: убирает обрывы, завершает предложением."""
        if not text:
            return text

        import re
        
        # Убираем эмоции в звездочках (*текст*)
        text = re.sub(r'\*[^*]+\*', '', text)
        
        # Убираем эмоции в подчеркиваниях (_текст_)
        text = re.sub(r'_[^_]+_', '', text)
        
        # Убираем эмоции в квадратных скобках [текст]
        text = re.sub(r'\[[^\]]+\]', '', text)
        
        # УЛУЧШЕНИЕ: Более агрессивная обработка смешанных языков
        # Проверяем наличие смешанных русско-английских слов
        mixed_pattern = r'([а-яА-ЯёЁ]+)([a-zA-Z]+)|([a-zA-Z]+)([а-яА-ЯёЁ]+)'
        if re.search(mixed_pattern, text):
            # Если найдены смешанные слова, пытаемся их разделить
            text = re.sub(r'([а-яА-ЯёЁ])([a-zA-Z])', r'\1 \2', text)
            text = re.sub(r'([a-zA-Z])([а-яА-ЯёЁ])', r'\1 \2', text)
            
            # Убираем одиночные английские слова в конце
            text = re.sub(r'\s+[a-zA-Z]+\s*$', '', text.strip())
            
            # Убираем одиночные английские слова в начале
            text = re.sub(r'^[a-zA-Z]+\s+', '', text.strip())
        
        # УЛУЧШЕНИЕ: Убираем английские слова, которые остались после обработки
        # Находим все английские слова
        english_words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        if english_words:
            # Убираем английские слова, оставляя только русский текст
            for word in english_words:
                text = re.sub(r'\b' + re.escape(word) + r'\b', '', text)
        
        # Убираем лишние пробелы и знаки препинания
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s*,\s*,+', ',', text)  # Убираем множественные запятые
        text = re.sub(r'\s*\.\s*\.+', '.', text)  # Убираем множественные точки
        
        # Если строка пустая после очистки
        if not text:
            return text
        
        # Найти последний маркер конца предложения
        sentence_endings = ['.', '!', '?', '…']
        last_end_index = max((text.rfind(sep) for sep in sentence_endings))

        if last_end_index != -1:
            finalized = text[: last_end_index + 1].strip()
        else:
            # Если совсем нет окончания, принудительно завершить короткой точкой
            finalized = text.rstrip()
            if not finalized.endswith('.'):
                finalized += '.'

        # Простейшая правка висящих кавычек/скобок в конце
        dangling = ['"', "'", '«', '"', '"', '„', '(', '[', '{']
        while finalized and finalized[-1] in dangling:
            finalized = finalized[:-1].rstrip()

        return finalized

    async def generate_response(self, messages: list, user_message: str = "") -> str:
        """Генерирует ответ"""
        if not self.is_loaded:
            return "❌ AI модель не загружена"
            
        try:
            # Формируем сообщения для chat-completions с учетом вашей истории
            chat_messages = []
            # Динамический системный промпт с актуальным временем по МСК
            # Используем кастомный промпт если задан, иначе стандартный
            if self.custom_system_prompt:
                system_prompt_text = self.custom_system_prompt
                # Подставляем динамические значения времени/активности/настроения
                system_prompt_text = self._format_prompt_with_context(system_prompt_text)
            else:
                system_prompt_text = get_system_prompt()
            if system_prompt_text:
                chat_messages.append({"role": "system", "content": system_prompt_text})
            if messages:
                for msg in messages:  # ограничим контекст
                    text = msg.get("text", "").strip()
                    if not text:
                        continue
                    role = "assistant" if msg.get("is_outgoing", False) else "user"
                    chat_messages.append({"role": role, "content": text})

            # Параметры генерации из AI_SETTINGS
            temperature = AI_SETTINGS.get('temperature', 0.7)
            top_p = AI_SETTINGS.get('top_p', 0.95)
            max_new_tokens = AI_SETTINGS.get('max_new_tokens', 200)
            repetition_penalty = AI_SETTINGS.get('repetition_penalty', 1.3)

            # Генерация через chat API (Llama 3 RP)
            response = self.model.create_chat_completion(
                messages=chat_messages,
                temperature=temperature,
                top_p=top_p,
                top_k=30,
                typical_p=0.98,
                min_p=0.05,
                max_tokens=max_new_tokens,
                repeat_penalty=repetition_penalty,
                stop=[
                    "User:", "Assistant:", "Ксюша:", "\nUser", "\nAssistant",
                    "я языковая модель", "Я языковая модель", "LMSYS", "организации больших моделей",
                    "language model", "Я модель", "я модель", "нейросеть",
                ]
            )
            
            # Извлекаем текст ответа
            if response and 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                # llama.cpp chat-completions помещает текст в message.content
                result = (choice.get('message', {}) or {}).get('content', '') or choice.get('text', '')
                result = (result or '').strip()
                # Переводим на русский если нужно
                result = self._translate_to_russian(result)
                # Завершаем предложение/обрезаем до полного
                result = self._finalize_response(result)
                return result if result else None
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации ответа: {e}")
            return None








































