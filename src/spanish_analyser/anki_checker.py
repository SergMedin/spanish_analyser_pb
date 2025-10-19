#!/usr/bin/env python3
"""
Модуль для проверки запущенного приложения Anki
"""

import os
import sys
import subprocess
import platform
from typing import List, Optional

class AnkiChecker:
    """Класс для проверки состояния приложения Anki"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.anki_process_names = self._get_anki_process_names()
    
    def _get_anki_process_names(self) -> List[str]:
        """Возвращает список имён процессов Anki для разных ОС"""
        if self.system == "darwin":  # macOS
            return ["Anki", "anki", "Anki.app"]
        elif self.system == "windows":
            return ["anki.exe", "Anki.exe", "anki"]
        elif self.system == "linux":
            return ["anki", "Anki", "anki-bin"]
        else:
            return ["anki", "Anki"]
    
    def is_anki_running(self) -> bool:
        """
        Проверяет, запущено ли приложение Anki
        
        Returns:
            bool: True если Anki запущено, False если нет
        """
        try:
            if self.system == "darwin":  # macOS
                return self._check_macos_anki()
            elif self.system == "windows":
                return self._check_windows_anki()
            elif self.system == "linux":
                return self._check_linux_anki()
            else:
                return self._check_generic_anki()
        except Exception as e:
            print(f"⚠️ Ошибка при проверке Anki: {e}")
            return False
    
    def _check_macos_anki(self) -> bool:
        """Проверка Anki на macOS"""
        try:
            # Используем ps для поиска процессов
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Ищем процессы Anki
            for line in result.stdout.split('\n'):
                if any(name in line for name in self.anki_process_names):
                    # Исключаем сам скрипт проверки
                    if "anki_checker" not in line and "python" not in line:
                        return True
            
            # Дополнительная проверка через Activity Monitor
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "Anki"], 
                    capture_output=True, 
                    text=True
                )
                if result.stdout.strip():
                    return True
            except:
                pass
                
            return False
            
        except subprocess.CalledProcessError:
            return False
    
    def _check_windows_anki(self) -> bool:
        """Проверка Anki на Windows"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq anki.exe"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Если в выводе есть "anki.exe", значит процесс запущен
            return "anki.exe" in result.stdout.lower()
            
        except subprocess.CalledProcessError:
            return False
    
    def _check_linux_anki(self) -> bool:
        """Проверка Anki на Linux"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "anki"], 
                capture_output=True, 
                text=True
            )
            
            return bool(result.stdout.strip())
            
        except subprocess.CalledProcessError:
            return False
    
    def _check_generic_anki(self) -> bool:
        """Универсальная проверка Anki"""
        try:
            if self.system == "darwin":
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            else:
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            
            return any(name in result.stdout for name in self.anki_process_names)
            
        except subprocess.CalledProcessError:
            return False
    
    def get_anki_processes(self) -> List[dict]:
        """
        Возвращает список запущенных процессов Anki с детальной информацией
        
        Returns:
            List[dict]: Список словарей с информацией о процессах
        """
        processes = []
        
        try:
            if self.system == "darwin":  # macOS
                result = subprocess.run(
                    ["ps", "aux"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                
                for line in result.stdout.split('\n'):
                    if any(name in line for name in self.anki_process_names):
                        # Парсим строку ps aux
                        parts = line.split()
                        if len(parts) >= 11:
                            process_info = {
                                'pid': parts[1],
                                'cpu': parts[2],
                                'mem': parts[3],
                                'command': ' '.join(parts[10:])
                            }
                            processes.append(process_info)
            
            elif self.system == "windows":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq anki.exe", "/FO", "CSV"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                
                for line in result.stdout.split('\n')[1:]:  # Пропускаем заголовок
                    if line.strip() and "anki.exe" in line.lower():
                        parts = line.split(',')
                        if len(parts) >= 5:
                            process_info = {
                                'pid': parts[1].strip('"'),
                                'mem': parts[4].strip('"'),
                                'command': parts[0].strip('"')
                            }
                            processes.append(process_info)
            
            elif self.system == "linux":
                result = subprocess.run(
                    ["ps", "aux"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                
                for line in result.stdout.split('\n'):
                    if any(name in line for name in self.anki_process_names):
                        parts = line.split()
                        if len(parts) >= 11:
                            process_info = {
                                'pid': parts[1],
                                'cpu': parts[2],
                                'mem': parts[3],
                                'command': ' '.join(parts[10:])
                            }
                            processes.append(process_info)
        
        except Exception as e:
            print(f"⚠️ Ошибка при получении списка процессов: {e}")
        
        return processes
    
    def wait_for_anki_to_close(self, timeout: int = 300) -> bool:
        """
        Ждёт, пока пользователь закроет Anki
        
        Args:
            timeout (int): Таймаут в секундах (по умолчанию 5 минут)
            
        Returns:
            bool: True если Anki закрыто, False если таймаут
        """
        import time
        
        print(f"⏳ Ожидаю закрытия Anki (таймаут: {timeout} сек)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_anki_running():
                print("✅ Anki успешно закрыто!")
                return True
            
            # Показываем прогресс каждые 10 секунд
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0:
                remaining = timeout - elapsed
                print(f"⏳ Прошло {elapsed} сек, осталось {remaining} сек...")
            
            time.sleep(1)
        
        print(f"⏰ Таймаут ожидания ({timeout} сек) истёк!")
        return False
    
    def show_anki_status(self) -> None:
        """Показывает текущий статус Anki"""
        if self.is_anki_running():
            print("🔴 Anki ЗАПУЩЕНО")
            processes = self.get_anki_processes()
            if processes:
                print(f"📋 Найдено процессов: {len(processes)}")
                for i, proc in enumerate(processes, 1):
                    print(f"   {i}. PID: {proc.get('pid', 'N/A')}")
                    if 'mem' in proc:
                        print(f"      Память: {proc['mem']}")
                    if 'command' in proc:
                        cmd = proc['command'][:50] + "..." if len(proc['command']) > 50 else proc['command']
                        print(f"      Команда: {cmd}")
        else:
            print("🟢 Anki НЕ ЗАПУЩЕНО")
    
    def request_anki_close(self) -> bool:
        """
        Просит пользователя закрыть Anki
        
        Returns:
            bool: True если пользователь согласился закрыть Anki
        """
        print("\n" + "="*60)
        print("🚨 ВНИМАНИЕ: Обнаружено запущенное приложение Anki!")
        print("="*60)
        
        self.show_anki_status()
        
        print("\n📝 Для корректной работы скрипта необходимо закрыть Anki.")
        print("   Это позволит получить доступ к базе данных Anki.")
        
        while True:
            print("\nВыберите действие:")
            print("1. Закрыть Anki и продолжить")
            print("2. Показать статус Anki")
            print("3. Отменить выполнение скрипта")
            
            try:
                choice = input("\nВведите номер (1-3): ").strip()
                
                if choice == "1":
                    print("\n🔄 Закрываю Anki...")
                    
                    # Пытаемся закрыть Anki
                    if self._try_close_anki():
                        print("✅ Anki успешно закрыто!")
                        return True
                    else:
                        print("⚠️ Не удалось автоматически закрыть Anki.")
                        print("   Пожалуйста, закройте Anki вручную и нажмите Enter...")
                        input()
                        
                        # Проверяем, закрылось ли Anki
                        if not self.is_anki_running():
                            print("✅ Anki закрыто! Продолжаем...")
                            return True
                        else:
                            print("❌ Anki всё ещё запущено. Попробуйте ещё раз.")
                            continue
                
                elif choice == "2":
                    self.show_anki_status()
                    continue
                
                elif choice == "3":
                    print("❌ Выполнение скрипта отменено.")
                    return False
                
                else:
                    print("❌ Неверный выбор. Введите 1, 2 или 3.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n\n❌ Выполнение скрипта прервано пользователем.")
                return False
            except EOFError:
                print("\n\n❌ Неожиданный конец ввода.")
                return False
    
    def _try_close_anki(self) -> bool:
        """
        Пытается автоматически закрыть Anki
        
        Returns:
            bool: True если удалось закрыть, False если нет
        """
        try:
            if self.system == "darwin":  # macOS
                # Пытаемся закрыть через osascript
                result = subprocess.run([
                    "osascript", "-e", 
                    'tell application "Anki" to quit'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    # Ждём немного и проверяем
                    import time
                    time.sleep(2)
                    return not self.is_anki_running()
                
            elif self.system == "windows":
                # Пытаемся закрыть через taskkill
                result = subprocess.run([
                    "taskkill", "/F", "/IM", "anki.exe"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    import time
                    time.sleep(2)
                    return not self.is_anki_running()
            
            elif self.system == "linux":
                # Пытаемся закрыть через pkill
                result = subprocess.run([
                    "pkill", "-f", "anki"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    import time
                    time.sleep(2)
                    return not self.is_anki_running()
        
        except Exception as e:
            print(f"⚠️ Ошибка при автоматическом закрытии Anki: {e}")
        
        return False


def check_anki_before_run() -> bool:
    """
    Функция для проверки Anki перед запуском основного скрипта
    
    Returns:
        bool: True если можно продолжать, False если нужно прервать выполнение
    """
    checker = AnkiChecker()
    
    if checker.is_anki_running():
        return checker.request_anki_close()
    else:
        print("✅ Anki не запущено, можно продолжать...")
        return True


if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля AnkiChecker")
    print("="*50)
    
    checker = AnkiChecker()
    checker.show_anki_status()
    
    if checker.is_anki_running():
        print("\n🔍 Детальная информация о процессах:")
        processes = checker.get_anki_processes()
        for proc in processes:
            print(f"   PID: {proc.get('pid', 'N/A')}")
            for key, value in proc.items():
                if key != 'pid':
                    print(f"      {key}: {value}")
    
    print(f"\n✅ Модуль AnkiChecker готов к использованию!")
