"""
Тесты для нового WordAnalyzer с разделением на компоненты.
"""

import pytest
from unittest.mock import Mock, patch
from src.spanish_analyser.components.tokenizer import TokenProcessor
from src.spanish_analyser.components.normalizer import WordNormalizer
from src.spanish_analyser.components.lemmatizer import LemmaProcessor
from src.spanish_analyser.components.pos_tagger import POSTagger
from src.spanish_analyser.components.frequency_analyzer import FrequencyAnalyzer
from src.spanish_analyser.components.word_comparator import WordComparator
from src.spanish_analyser.components.exporter import ResultExporter
from src.spanish_analyser.word_analyzer import WordAnalyzer
from src.spanish_analyser.interfaces.text_processor import AnalysisResult, WordInfo


class TestWordAnalyzer:
    """Тесты для нового WordAnalyzer."""
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_init(self, mock_pos_load, mock_lemma_load):
        """Тест инициализации."""
        # Мокаем загрузку spaCy моделей
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        assert isinstance(analyzer.tokenizer, TokenProcessor)
        assert isinstance(analyzer.lemmatizer, LemmaProcessor)
        assert isinstance(analyzer.pos_tagger, POSTagger)
        assert isinstance(analyzer.frequency_analyzer, FrequencyAnalyzer)
        assert isinstance(analyzer.word_comparator, WordComparator)
        assert isinstance(analyzer.word_normalizer, WordNormalizer)
        assert isinstance(analyzer.exporter, ResultExporter)
        
        assert analyzer.min_word_length == 3
        # Проверяем, что модель берётся из конфигурации (может быть es_core_news_md или es_dep_news_trf)
        assert analyzer.spacy_model in ["es_core_news_md", "es_dep_news_trf"]
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_init_with_custom_params(self, mock_pos_load, mock_lemma_load):
        """Тест инициализации с пользовательскими параметрами."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer(
            min_word_length=5,
            spacy_model="es_core_news_sm",
            output_dir="custom/output"
        )
        
        assert analyzer.min_word_length == 5
        assert analyzer.spacy_model == "es_core_news_sm"
        assert str(analyzer.exporter.output_dir) == "custom/output"
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_analyze_text_empty(self, mock_pos_load, mock_lemma_load):
        """Тест анализа пустого текста."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        result = analyzer.analyze_text("")
        assert result.total_words == 0
        assert result.unique_words == 0
        assert len(result.words) == 0
        
        result = analyzer.analyze_text("   ")
        assert result.total_words == 0
        assert result.unique_words == 0
        assert len(result.words) == 0
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_analyze_text_simple(self, mock_pos_load, mock_lemma_load):
        """Тест анализа простого текста."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем поведение компонентов
        analyzer.tokenizer.tokenize = Mock(return_value=["hola", "mundo"])
        analyzer.lemmatizer.lemmatize_batch = Mock(return_value=["hola", "mundo"])
        analyzer.pos_tagger.get_pos_tags = Mock(return_value=["NOUN", "NOUN"])
        analyzer.pos_tagger.get_pos_tag_ru = Mock(side_effect=["Существительное", "Существительное"])
        analyzer.frequency_analyzer.count_frequency = Mock(return_value={"hola": 1, "mundo": 1})
        analyzer.word_comparator.is_word_known = Mock(return_value=False)
        analyzer.word_comparator.filter_unknown_words = Mock(return_value=["hola", "mundo"])
        
        result = analyzer.analyze_text("Hola mundo")
        
        assert result.total_words == 2
        assert result.unique_words == 2
        assert len(result.words) == 2
        assert len(result.unknown_words) == 2
        assert result.processing_time > 0
        
        # Проверяем, что все компоненты были вызваны
        analyzer.tokenizer.tokenize.assert_called_once()
        analyzer.lemmatizer.lemmatize_batch.assert_called_once()
        analyzer.pos_tagger.get_pos_tags.assert_called_once()
        analyzer.frequency_analyzer.count_frequency.assert_called_once()
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_get_unknown_words_for_learning(self, mock_pos_load, mock_lemma_load):
        """Тест получения слов для изучения."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Создаём тестовый результат
        words_info = [
            WordInfo(word="hola", pos_tag="NOUN", pos_tag_ru="Существительное", 
                    frequency=2, lemma="hola", is_known=False),
            WordInfo(word="mundo", pos_tag="NOUN", pos_tag_ru="Существительное", 
                    frequency=1, lemma="mundo", is_known=False),
            WordInfo(word="el", pos_tag="DET", pos_tag_ru="Определитель", 
                    frequency=3, lemma="el", is_known=True)
        ]
        
        result = AnalysisResult(
            words=words_info,
            frequency_dict={"hola": 2, "mundo": 1, "el": 3},
            unknown_words=["hola", "mundo"],
            total_words=3,
            unique_words=3,
            processing_time=0.1
        )
        
        # Мокаем приоритеты частей речи
        analyzer.pos_tagger.get_learning_priority = Mock(side_effect=lambda pos: 10 if pos == "NOUN" else 5)
        
        unknown_words = analyzer.get_unknown_words_for_learning(result)
        
        assert len(unknown_words) == 2
        assert unknown_words[0].word == "hola"  # Большая частота
        assert unknown_words[1].word == "mundo"  # Меньшая частота
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_get_statistics(self, mock_pos_load, mock_lemma_load):
        """Тест получения статистики."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем статистику компонентов
        analyzer.tokenizer.get_token_statistics = Mock(return_value={"total_tokens": 0})
        analyzer.lemmatizer.get_cache_stats = Mock(return_value={"cache_size": 5})
        analyzer.pos_tagger.is_model_loaded = Mock(return_value=True)
        analyzer.frequency_analyzer.get_frequency_statistics = Mock(return_value={"total_words": 10})
        analyzer.word_comparator.get_comparison_statistics = Mock(return_value={"known_words_count": 100})
        analyzer.word_normalizer.get_cache_stats = Mock(return_value={"cache_size": 3})
        
        stats = analyzer.get_statistics()
        
        assert "tokenizer" in stats
        assert "lemmatizer" in stats
        assert "pos_tagger" in stats
        assert "frequency_analyzer" in stats
        assert "word_comparator" in stats
        assert "word_normalizer" in stats
        assert "settings" in stats
        
        assert stats["settings"]["min_word_length"] == 3
        # Проверяем, что модель берётся из конфигурации (может быть es_core_news_md или es_dep_news_trf)
        assert stats["settings"]["spacy_model"] in ["es_core_news_md", "es_dep_news_trf"]
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_clear_caches(self, mock_pos_load, mock_lemma_load):
        """Тест очистки кэшей."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем методы очистки
        analyzer.lemmatizer.clear_cache = Mock()
        analyzer.word_normalizer.clear_cache = Mock()
        analyzer.frequency_analyzer.reset_statistics = Mock()
        
        analyzer.clear_caches()
        
        analyzer.lemmatizer.clear_cache.assert_called_once()
        analyzer.word_normalizer.clear_cache.assert_called_once()
        analyzer.frequency_analyzer.reset_statistics.assert_called_once()
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_reload_models(self, mock_pos_load, mock_lemma_load):
        """Тест перезагрузки моделей."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем перезагрузку
        analyzer.lemmatizer.reload_model = Mock(return_value=True)
        analyzer.pos_tagger.reload_model = Mock(return_value=True)
        
        success = analyzer.reload_models()
        
        assert success is True
        analyzer.lemmatizer.reload_model.assert_called_once()
        analyzer.pos_tagger.reload_model.assert_called_once()
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_backward_compatibility(self, mock_pos_load, mock_lemma_load):
        """Тест обратной совместимости."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем компоненты для анализа
        analyzer.tokenizer.tokenize = Mock(return_value=["hola", "mundo"])
        analyzer.lemmatizer.lemmatize_batch = Mock(return_value=["hola", "mundo"])
        analyzer.pos_tagger.get_pos_tags = Mock(return_value=["NOUN", "NOUN"])
        analyzer.pos_tagger.get_pos_tag_ru = Mock(side_effect=["Существительное", "Существительное"])
        analyzer.frequency_analyzer.count_frequency = Mock(return_value={"hola": 1, "mundo": 1})
        analyzer.word_comparator.is_word_known = Mock(return_value=False)
        analyzer.word_comparator.filter_unknown_words = Mock(return_value=["hola", "mundo"])
        
        # Тестируем старый API
        old_result = analyzer.analyze_spanish_text("Hola mundo")
        
        assert "words" in old_result
        assert "frequencies" in old_result
        assert "unknown_words" in old_result
        assert "total_words" in old_result
        assert "unique_words" in old_result
        assert "processing_time" in old_result
        assert "pos_tags" in old_result
        
        assert old_result["words"] == ["hola", "mundo"]
        assert old_result["frequencies"] == {"hola": 1, "mundo": 1}
        assert old_result["unknown_words"] == ["hola", "mundo"]
        assert old_result["total_words"] == 2
        assert old_result["unique_words"] == 2
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_get_word_frequency_backward_compatibility(self, mock_pos_load, mock_lemma_load):
        """Тест обратной совместимости get_word_frequency."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем frequency analyzer
        analyzer.frequency_analyzer.get_word_frequency = Mock(return_value=5)
        
        frequency = analyzer.get_word_frequency("hola")
        assert frequency == 5
        analyzer.frequency_analyzer.get_word_frequency.assert_called_once_with("hola")
    
    @patch('src.spanish_analyser.components.lemmatizer.spacy.load')
    @patch('src.spanish_analyser.components.pos_tagger.spacy.load')
    def test_get_most_frequent_words_backward_compatibility(self, mock_pos_load, mock_lemma_load):
        """Тест обратной совместимости get_most_frequent_words."""
        mock_nlp = Mock()
        mock_lemma_load.return_value = mock_nlp
        mock_pos_load.return_value = mock_nlp
        
        analyzer = WordAnalyzer()
        
        # Мокаем frequency analyzer
        expected_result = [("hola", 5), ("mundo", 3)]
        analyzer.frequency_analyzer.get_most_frequent = Mock(return_value=expected_result)
        
        result = analyzer.get_most_frequent_words(2)
        assert result == expected_result
        analyzer.frequency_analyzer.get_most_frequent.assert_called_once_with(2)
