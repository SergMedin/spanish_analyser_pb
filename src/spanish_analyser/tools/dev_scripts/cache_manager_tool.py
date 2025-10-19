#!/usr/bin/env python3
"""
Утилита для управления кэшем проекта.

Возможности:
- Просмотр содержимого кэша с читаемыми именами файлов
- Очистка отдельных пулов кэша
- Поиск файлов кэша по содержимому (модель, слово и т.д.)
- Статистика использования кэша
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parents[2]))

from spanish_analyser.cache import CacheManager
from spanish_analyser.config import config
import argparse


def list_cache_files(pool: str = None, pattern: str = None):
    """Показывает файлы кэша с их читаемыми именами."""
    cache_root = Path(config.get_cache_root_dir())
    
    pools_to_check = [pool] if pool else ['html', 'anki', 'spacy', 'openai']
    
    print("📁 Файлы кэша:")
    for pool_name in pools_to_check:
        pool_dir = cache_root / pool_name
        if not pool_dir.exists():
            continue
            
        files = list(pool_dir.glob("*.bin"))
        if pattern:
            files = [f for f in files if pattern.lower() in f.name.lower()]
            
        if files:
            print(f"\n{pool_name.upper()} ({len(files)} файлов):")
            for file in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
                size_kb = file.stat().st_size / 1024
                mtime = file.stat().st_mtime
                age_hours = (os.path.getmtime(__file__) - mtime) / 3600 if mtime else 0
                print(f"  {file.name} ({size_kb:.1f}KB, {age_hours:.1f}h назад)")


def clear_cache(pool: str = None, pattern: str = None, confirm: bool = True):
    """Очищает кэш для указанного пула или по паттерну."""
    cache_root = Path(config.get_cache_root_dir())
    
    pools_to_clear = [pool] if pool else ['html', 'anki', 'spacy', 'openai']
    files_to_remove = []
    
    for pool_name in pools_to_clear:
        pool_dir = cache_root / pool_name
        if not pool_dir.exists():
            continue
            
        files = list(pool_dir.glob("*.bin"))
        if pattern:
            files = [f for f in files if pattern.lower() in f.name.lower()]
            
        files_to_remove.extend(files)
    
    if not files_to_remove:
        print("🤷 Нет файлов для удаления")
        return
        
    print(f"🗑️  Будет удалено {len(files_to_remove)} файлов:")
    for file in files_to_remove:
        print(f"  {file.relative_to(cache_root)}")
    
    if confirm:
        response = input("\nПродолжить? (да/нет): ").strip().lower()
        if response not in ['да', 'yes', 'y', '1']:
            print("❌ Отменено")
            return
    
    removed = 0
    for file in files_to_remove:
        try:
            file.unlink()
            removed += 1
        except Exception as e:
            print(f"❌ Не удалось удалить {file.name}: {e}")
    
    print(f"✅ Удалено {removed} файлов")


def show_stats():
    """Показывает статистику кэша."""
    cache = CacheManager.get_cache()
    stats = cache.stats_dict()
    
    print("📊 Статистика кэша:")
    print(f"  Общие показатели:")
    print(f"    Hits: {stats['hits']}")
    print(f"    Misses: {stats['misses']}")
    print(f"    Expired: {stats['expired']}")
    print(f"    Stores: {stats['stores']}")
    print(f"    Errors: {stats['errors']}")
    
    print(f"\n  По пулам:")
    for pool, pool_stats in stats['by_bucket'].items():
        if any(pool_stats.values()):
            print(f"    {pool}: hits={pool_stats['hits']}, stores={pool_stats['stores']}, expired={pool_stats['expired']}")
    
    print(f"\n  Настройки:")
    print(f"    Корневая папка: {stats['root']}")
    print(f"    Лимит на пул: {stats['limit_mb_per_bucket']} MB")
    
    print(f"\n  TTL (дни):")
    for pool, ttl in stats['ttl_days'].items():
        enabled = stats['enabled'][pool]
        status = "✅" if enabled else "❌"
        print(f"    {pool}: {ttl} дней {status}")
    
    print(f"\n  Размеры пулов:")
    for pool, size_info in stats['sizes'].items():
        if size_info['files'] > 0:
            print(f"    {pool}: {size_info['files']} файлов, {size_info['size_mb']} MB")


def main():
    parser = argparse.ArgumentParser(description="Управление кэшем проекта")
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда list
    list_parser = subparsers.add_parser('list', help='Показать файлы кэша')
    list_parser.add_argument('--pool', choices=['html', 'anki', 'spacy', 'openai'], help='Фильтр по пулу')
    list_parser.add_argument('--pattern', help='Фильтр по содержимому имени файла')
    
    # Команда clear
    clear_parser = subparsers.add_parser('clear', help='Очистить кэш')
    clear_parser.add_argument('--pool', choices=['html', 'anki', 'spacy', 'openai'], help='Очистить конкретный пул')
    clear_parser.add_argument('--pattern', help='Очистить файлы по паттерну')
    clear_parser.add_argument('--force', action='store_true', help='Не запрашивать подтверждение')
    
    # Команда stats
    subparsers.add_parser('stats', help='Показать статистику кэша')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_cache_files(args.pool, args.pattern)
    elif args.command == 'clear':
        clear_cache(args.pool, args.pattern, not args.force)
    elif args.command == 'stats':
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
