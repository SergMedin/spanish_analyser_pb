"""
Компонент для экспорта результатов анализа.

Отвечает за экспорт результатов в различные форматы:
Excel, CSV для Anki, JSON с временными метками.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Any
import pandas as pd
from ..interfaces.text_processor import ResultExporterInterface, AnalysisResult, WordInfo
import logging

logger = logging.getLogger(__name__)


class ResultExporter(ResultExporterInterface):
    """Экспортёр результатов анализа."""
    
    def __init__(self, output_dir: str = "data/results"):
        """
        Инициализирует экспортёр.
        
        Args:
            output_dir: Папка для сохранения результатов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_excel(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """
        Экспортирует результат в Excel формат.
        
        Args:
            result: Результат анализа
            filepath: Путь для сохранения файла
        """
        if not result or not result.words:
            logger.info("Нет данных для экспорта в Excel")
            return
        
        try:
            # Подготавливаем данные для Excel
            excel_data = []
            
            for word_info in result.words:
                excel_data.append({
                    'Слово': word_info.word,
                    'Лемма': word_info.lemma,
                    'Часть речи': word_info.pos_tag_ru,
                    'Род': word_info.gender or '',
                    'Частота': word_info.frequency,
                    'Известно': 'Да' if word_info.is_known else 'Нет',
                    'Комментарии': word_info.comment or '',
                    'Примеры контекста': '; '.join(word_info.context_examples) if word_info.context_examples else ''
                })
            
            # Создаём DataFrame
            df = pd.DataFrame(excel_data)

            # Схлопываем по словам: для каждого уникального слова оставляем строку
            # с максимальной частотой (последний шаг перед выгрузкой в Excel)
            try:
                before_count = len(df)
                # Сортируем по слову (asc), затем по частоте (desc) для детерминированности
                df = df.sort_values(['Слово', 'Частота'], ascending=[True, False], kind='stable')
                # Удаляем дубликаты слов, оставляя первую (с максимальной частотой)
                df = df.drop_duplicates(subset=['Слово'], keep='first').reset_index(drop=True)
                after_count = len(df)
                if after_count < before_count:
                    logger.info(f"Схлопнуто по словам: было {before_count}, осталось {after_count}")
            except Exception as e:
                # В случае неожиданных проблем со схлопыванием — не прерываем экспорт
                logger.warning(f"Не удалось схлопнуть по словам: {e}")
            
            # Создаём Excel writer
            filepath = Path(filepath)
            if not filepath.suffix:
                filepath = filepath.with_suffix('.xlsx')
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Основная таблица со словами
                df.to_excel(writer, sheet_name='Слова для изучения', index=False)
                
                # Статистика
                stats_data = {
                    'Параметр': [
                        'Общее количество слов',
                        'Уникальных слов',
                        'Неизвестных слов',
                        'Время обработки (сек)',
                        'Доля X/SYM',
                        'Доля основных POS (NOUN/VERB/ADJ)',
                        'Дата анализа'
                    ],
                    'Значение': [
                        result.total_words,
                        result.unique_words,
                        len(result.unknown_words),
                        round(result.processing_time, 2),
                        round(float(result.metadata.get('x_sym_ratio', 0.0)), 4) if result.metadata else 0.0,
                        round(float(result.metadata.get('main_pos_ratio', 0.0)), 4) if result.metadata else 0.0,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Статистика', index=False)
                
                # Частотность
                if result.frequency_dict:
                    freq_data = [
                        {'Слово': word, 'Частота': freq}
                        for word, freq in sorted(result.frequency_dict.items(), key=lambda x: x[1], reverse=True)
                    ]
                    freq_df = pd.DataFrame(freq_data)
                    freq_df.to_excel(writer, sheet_name='Частотность', index=False)
            
            print(f"Результат экспортирован в Excel: {filepath}")
            
        except Exception as e:
            print(f"Ошибка экспорта в Excel: {e}")
    
    def export_to_csv(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """
        Экспортирует результат в CSV формат для Anki.
        
        Args:
            result: Результат анализа
            filepath: Путь для сохранения файла
        """
        if not result or not result.words:
            logger.info("Нет данных для экспорта в CSV")
            return
        
        try:
            filepath = Path(filepath)
            if not filepath.suffix:
                filepath = filepath.with_suffix('.csv')
            
            # Фильтруем только неизвестные слова
            unknown_words = [word_info for word_info in result.words if not word_info.is_known]
            
            if not unknown_words:
                print("Нет неизвестных слов для экспорта в Anki")
                return
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Заголовки для Anki
                writer.writerow(['FrontText', 'BackText', 'Tags'])
                
                for word_info in unknown_words:
                    # Формируем переднюю сторону карточки
                    front_text = word_info.word
                    
                    # Формируем заднюю сторону карточки
                    back_text = f"{word_info.pos_tag_ru}\nЛемма: {word_info.lemma}\nЧастота: {word_info.frequency}"
                    
                    # Теги
                    tags = f"spanish,{word_info.pos_tag.lower()},frequency_{word_info.frequency}"
                    
                    writer.writerow([front_text, back_text, tags])
            
            logger.info(f"Результат экспортирован в CSV для Anki: {filepath}")
            logger.info(f"Экспортировано {len(unknown_words)} слов для изучения")
            
        except Exception as e:
            print(f"Ошибка экспорта в CSV: {e}")
    
    def export_to_json(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """
        Экспортирует результат в JSON формат.
        
        Args:
            result: Результат анализа
            filepath: Путь для сохранения файла
        """
        if not result:
            print("Нет данных для экспорта в JSON")
            return
        
        try:
            filepath = Path(filepath)
            if not filepath.suffix:
                filepath = filepath.with_suffix('.json')
            
            # Подготавливаем данные для JSON
            json_data = {
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'total_words': result.total_words,
                    'unique_words': result.unique_words,
                    'unknown_words_count': len(result.unknown_words),
                    'processing_time': result.processing_time
                },
                'words': [
                    {
                        'word': word_info.word,
                        'lemma': word_info.lemma,
                        'pos_tag': word_info.pos_tag,
                        'pos_tag_ru': word_info.pos_tag_ru,
                        'frequency': word_info.frequency,
                        'is_known': word_info.is_known,
                        'context_examples': word_info.context_examples or []
                    }
                    for word_info in result.words
                ],
                'frequency_dict': result.frequency_dict,
                'unknown_words': result.unknown_words,
                'additional_metadata': result.metadata or {}
            }
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, ensure_ascii=False, indent=2)
            
            logger.info(f"Результат экспортирован в JSON: {filepath}")
            
        except Exception as e:
            print(f"Ошибка экспорта в JSON: {e}")
    
    def export_summary_report(self, result: AnalysisResult, filepath: Union[str, Path]) -> None:
        """
        Экспортирует краткий отчёт по результатам.
        
        Args:
            result: Результат анализа
            filepath: Путь для сохранения файла
        """
        if not result:
            print("Нет данных для экспорта отчёта")
            return
        
        try:
            filepath = Path(filepath)
            if not filepath.suffix:
                filepath = filepath.with_suffix('.txt')
            
            with open(filepath, 'w', encoding='utf-8') as report_file:
                report_file.write("ОТЧЁТ ПО АНАЛИЗУ ИСПАНСКОГО ТЕКСТА\n")
                report_file.write("=" * 50 + "\n\n")
                
                # Общая статистика
                report_file.write("ОБЩАЯ СТАТИСТИКА:\n")
                report_file.write(f"Общее количество слов: {result.total_words}\n")
                report_file.write(f"Уникальных слов: {result.unique_words}\n")
                report_file.write(f"Неизвестных слов: {len(result.unknown_words)}\n")
                report_file.write(f"Время обработки: {result.processing_time:.2f} сек\n")
                report_file.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Топ неизвестных слов
                if result.words:
                    unknown_words = [w for w in result.words if not w.is_known]
                    if unknown_words:
                        report_file.write("ТОП НЕИЗВЕСТНЫХ СЛОВ ДЛЯ ИЗУЧЕНИЯ:\n")
                        report_file.write("-" * 40 + "\n")
                        
                        # Сортируем по частоте и приоритету
                        sorted_words = sorted(
                            unknown_words,
                            key=lambda x: (x.frequency, x.pos_tag),
                            reverse=True
                        )
                        
                        for i, word_info in enumerate(sorted_words[:20], 1):
                            report_file.write(
                                f"{i:2d}. {word_info.word:<15} "
                                f"({word_info.pos_tag_ru:<12}) "
                                f"Частота: {word_info.frequency}\n"
                            )
                
                # Статистика по частям речи
                if result.words:
                    pos_stats = {}
                    for word_info in result.words:
                        pos = word_info.pos_tag_ru
                        pos_stats[pos] = pos_stats.get(pos, 0) + 1
                    
                    if pos_stats:
                        report_file.write("\nРАСПРЕДЕЛЕНИЕ ПО ЧАСТЯМ РЕЧИ:\n")
                        report_file.write("-" * 40 + "\n")
                        for pos, count in sorted(pos_stats.items(), key=lambda x: x[1], reverse=True):
                            report_file.write(f"{pos}: {count}\n")
            
            logger.info(f"Краткий отчёт сохранён: {filepath}")
            
        except Exception as e:
            print(f"Ошибка экспорта отчёта: {e}")
    
    def export_all_formats(self, result: AnalysisResult, base_filename: str) -> Dict[str, Path]:
        """
        Экспортирует результат во все доступные форматы.
        
        Args:
            result: Результат анализа
            base_filename: Базовое имя файла без расширения
            
        Returns:
            Словарь с путями к экспортированным файлам
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{base_filename}_{timestamp}"
        
        exported_files = {}
        
        try:
            # Excel
            excel_path = self.output_dir / f"{base_filename}.xlsx"
            self.export_to_excel(result, excel_path)
            exported_files['excel'] = excel_path
            
            # CSV для Anki
            csv_path = self.output_dir / f"{base_filename}_anki.csv"
            self.export_to_csv(result, csv_path)
            exported_files['csv'] = csv_path
            
            # JSON
            json_path = self.output_dir / f"{base_filename}.json"
            self.export_to_json(result, json_path)
            exported_files['json'] = json_path
            
            # Отчёт
            report_path = self.output_dir / f"{base_filename}_report.txt"
            self.export_summary_report(result, report_path)
            exported_files['report'] = report_path
            
            logger.info(f"Результат экспортирован во все форматы в папку: {self.output_dir}")
            
        except Exception as e:
            print(f"Ошибка при экспорте во все форматы: {e}")
        
        return exported_files
