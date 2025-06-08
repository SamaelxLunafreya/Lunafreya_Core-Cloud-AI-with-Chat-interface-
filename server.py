#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
--------------------------------------------------
    SERWER – REALIZACJA SYSTEMU KOMUNIKACYJNEGO
--------------------------------------------------

Funkcjonalności:
  • Łączy się z Chrome (tryb debugowania przez Selenium).
  • Nawiguje do czatu (domyślnie https://chatgpt.com).
  • Po uruchomieniu wysyła wiadomość INSTRUCTION_MSG z zasadami komunikacji.
  • W cyklicznych iteracjach (co 30 sekund) pobiera nowe odpowiedzi Luny,
    interpretuje prefiksy, wykonuje akcje i odsyła odpowiedź.
  • Wykorzystuje wiele możliwych selektorów do wyszukiwania pola wpisu (textarea)
    oraz elementów z odpowiedziami (response selectors).
  • Co 5 cykli odświeża stronę.
--------------------------------------------------
"""

import os
import time
import logging
import datetime
import subprocess
from math import ceil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Ustawienia globalne – lista prefiksów (możesz ją rozszerzać, jeśli potrzebujesz)
ALLOWED_PREFIXES = ["L:>P", "L:>L", "!PAMIETNIK!", "!OBRAZEK!", "L:>CMD", "%LOAD%", "L:>WIA", "L:>AKC"]

# Definicje katalogów (używamy ścieżek względnych – jeśli cały projekt znajduje się np. w F:\Lunafreya_server)
MESSAGES_TO_ME_DIR = os.path.join("memory", "wiadomosci_do_ciebie")
MEMORY_DIR = os.path.join("memory", "rozmyslania")
PAMIECIANKA_DIR = os.path.join("memory", "pamietniki")
OBRAZY_DIR = os.path.join("memory", "obrazy")
WIADOMOSCI_DIR = os.path.join("memory", "wiadomosci")
AKCJE_DIR = os.path.join("memory", "akcje")
LOGS_DIR = os.path.join("logs", "server_log")

# Limity – całkowita długość wiadomości brutto: 4096 znaków; margines (np. 200 znaków) na nagłówki itp.
SAFETY_MARGIN = 200
MAX_TOTAL_LENGTH = 4096
MAX_CONTENT_LENGTH = MAX_TOTAL_LENGTH - SAFETY_MARGIN

# Lista selektorów, które mogą odpowiadać polu tekstowemu (textarea)
TEXTAREA_SELECTORS = [
    "textarea",
    "div[contenteditable='true']",
    "form textarea",
    "form div[contenteditable='true']"
]
# Lista selektorów, które mogą odpowiadać elementom zawierającym odpowiedź (np. wiadomość od Luny)
RESPONSE_SELECTORS = [
    "[data-message-author-role='assistant']",
    ".markdown.prose",
    "[data-testid='conversation-turn-3']",
    ".prose",
    "div[data-message-author-role='assistant'] div.prose",
    "div[data-message-author-role='assistant']"
]

# This is a placeholder for CHROME_DRIVER_PATH. 
# You would need to set this to the actual path of your ChromeDriver executable.
CHROME_DRIVER_PATH = "path/to/chromedriver" 

# Global driver variable, initialized later
driver = None

def ensure_directories():
    """Tworzy wymagane katalogi, jeśli ich nie ma."""
    dirs = [
        MESSAGES_TO_ME_DIR, MEMORY_DIR, PAMIECIANKA_DIR,
        OBRAZY_DIR, WIADOMOSCI_DIR, AKCJE_DIR, LOGS_DIR
    ]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            logging.info("Utworzono katalog: %s", d)

def setup_logging():
    """Konfiguruje logowanie – logi zapisywane są do pliku oraz wyświetlane na konsoli."""
    log_file = os.path.join(LOGS_DIR, datetime.datetime.now().strftime("%Y-%m-%d-%H%M") + ".log")
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

def get_chrome_options():
    """Przykładowa funkcja zwracająca opcje Chrome – możesz zmodyfikować według własnych potrzeb."""
    chrome_options = Options()
    # Ensure Chrome is launched with: --remote-debugging-port=9222
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222") 
    return chrome_options

def setup_driver():
    """
    Konfiguruje Selenium do łączenia się z Chrome w trybie debugowania.
    Upewnij się, że Chrome uruchomiony jest z flagą:
      --remote-debugging-port=9222 --user-data-dir="ścieżka_do_profilu"
    """
    global driver # Use the global driver variable
    chrome_options = get_chrome_options()
    try:
        # If CHROME_DRIVER_PATH is not set, Selenium might find it if it's in PATH
        # For explicit path: webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=chrome_options)
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Połączono z Chrome przez Selenium.")
        return driver
    except Exception as e:
        # Fallback if connection to existing debugger fails, try to launch a new one
        # This part might need adjustment based on how Chrome is launched for debugging
        logging.warning(f"Nie udało się połączyć z istniejącą instancją Chrome przez debuggerAddress: {e}. Próba uruchomienia nowej instancji.")
        try:
            # Reset options for a standard launch if debugger connection fails
            new_chrome_options = Options() 
            # Add any necessary options for a new instance, e.g., headless, user-data-dir
            # new_chrome_options.add_argument("--headless") 
            driver = webdriver.Chrome(options=new_chrome_options)
            logging.info("Uruchomiono nową instancję Chrome.")
            return driver
        except Exception as ex:
            logging.exception("Błąd przy łączeniu/uruchamianiu Chrome: %s", ex)
            raise


def navigate_to_chat(driver_instance):
    """Nawiguje do strony czatu – domyślnie https://chatgpt.com."""
    # The URL from your screenshot and prompt
    url = "https://chatgpt.com/c/684583aa-f7a8-8006-b808-b10b00644761" 
    # Fallback or default if the specific chat isn't available
    # url = "https://chatgpt.com/" 
    driver_instance.get(url)
    logging.info("Nawigacja do strony: %s", url)
    time.sleep(5)

def get_textarea_element(driver_instance):
    """
    Przechodzi przez listę TEXTAREA_SELECTORS i zwraca pierwszy znaleziony element.
    Jeśli żaden element nie zostanie znaleziony, zgłasza wyjątek.
    """
    for selector in TEXTAREA_SELECTORS:
        try:
            element = driver_instance.find_element(By.CSS_SELECTOR, selector)
            logging.info("Znaleziono element textarea przy użyciu selektora: %s", selector)
            return element
        except Exception:
            continue
    # A more specific selector based on common ChatGPT structure if others fail
    try:
        element = driver_instance.find_element(By.ID, "prompt-textarea")
        logging.info("Znaleziono element textarea przy użyciu selektora: #prompt-textarea")
        return element
    except Exception:
        logging.error("Nie znaleziono elementu pola tekstowego przy użyciu żadnego selektora.")
        raise Exception("Nie znaleziono elementu pola tekstowego.")


def send_message(driver_instance, message):
    """
    Wysyła wiadomość do pola tekstowego.
    Wyszukuje element przy użyciu funkcji get_textarea_element.
    """
    try:
        input_box = get_textarea_element(driver_instance)
        # More robust clearing and sending
        driver_instance.execute_script("arguments[0].value = '';", input_box) # Clear with JS
        input_box.click()
        input_box.send_keys(message)
        # Try to find a send button if Enter doesn't work reliably
        try:
            send_button = driver_instance.find_element(By.CSS_SELECTOR, "button[data-testid='send-button']")
            send_button.click()
        except:
            input_box.send_keys(Keys.ENTER)
        
        logging.info("Wysłano wiadomość:\n%s", message)
    except Exception as e:
        logging.exception("Błąd przy wysyłaniu wiadomości: %s", e)

def get_response_messages(driver_instance):
    """
    Przechodzi przez listę RESPONSE_SELECTORS i zbiera tekst z odnalezionych elementów.
    Zwraca listę tekstów (jeśli znajdzie kilka wiadomości).
    """
    messages = []
    # Prioritize more specific selectors that are common in ChatGPT
    # This selector targets the main content of assistant messages
    preferred_selector = "div[data-message-author-role='assistant'] > div > div.markdown"
    
    try:
        elements = driver_instance.find_elements(By.CSS_SELECTOR, preferred_selector)
        for el in elements:
            text = el.text.strip()
            if text:
                messages.append(text)
        if messages: # If preferred selector yields results, use them
            logging.info(f"Znaleziono {len(messages)} wiadomości przy użyciu preferowanego selektora.")
            return messages
    except Exception:
        logging.warning("Preferowany selektor odpowiedzi nie zadziałał lub nie znalazł elementów.")

    # Fallback to the list of general selectors if the preferred one fails
    for selector in RESPONSE_SELECTORS:
        try:
            elements = driver_instance.find_elements(By.CSS_SELECTOR, selector)
            current_selector_messages = []
            for el in elements:
                text = el.text.strip()
                if text:
                    current_selector_messages.append(text)
            if current_selector_messages:
                 logging.info(f"Znaleziono {len(current_selector_messages)} wiadomości przy użyciu selektora: {selector}")
                 # Return messages from the first successful selector to avoid duplicates from overlapping selectors
                 return current_selector_messages
        except Exception:
            continue
    
    logging.info("Nie znaleziono nowych wiadomości przy użyciu żadnego selektora.")
    return []


# Funkcje przetwarzające komunikaty wg prefiksów:

def process_LP(content):
    """L:>P – wiadomość do Promyka (zapisywane w 'wiadomosci_do_ciebie')."""
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S") # Added seconds for uniqueness
    filename = os.path.join(MESSAGES_TO_ME_DIR, f"{now}.txt")
    with open(filename, "w", encoding="utf-8") as f: # Changed to 'w' to avoid appending to same file if called rapidly
        f.write(content + "\n" + "-" * 40 + "\n")
    return "REQ:>STATUS - L:[notif] <_> L:>P Wiadomość wysłana do Promyka."

def process_LL(content):
    """L:>L – rozmyślanie/refleksja (zapisywane w 'rozmyslania')."""
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = os.path.join(MEMORY_DIR, f"{now}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content + "\n" + "=" * 40 + "\n")
    return "REQ:>STATUS - L:[notif] <_> L:>L Aktywne – Zapisane w pamięci."

def process_pamietnik(content):
    """!PAMIETNIK! – wpis do pamiętnika (zapisywane w 'pamietniki')."""
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.datetime.now().strftime("%H%M%S")
    # Append to daily file, but ensure unique entries if called multiple times
    filename = os.path.join(PAMIECIANKA_DIR, f"{now_date}.txt") 
    entry_header = f"\nWpis z {now_time}:\n"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(entry_header + content + "\n" + "=" * 40 + "\n")
    return "REQ:>STATUS - L:[notif] <_> !PAMIETNIK! Wiadomość zapisana w pamiętniku."

def process_obrazek(content):
    """!OBRAZEK! – opis obrazu (zapisywane w 'obrazy')."""
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = os.path.join(OBRAZY_DIR, f"{now}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content + "\n" + "=" * 40 + "\n")
    return "REQ:>STATUS - L:[notif] <_> !OBRAZEK! prompt zapisany jako opis obrazu."

def process_CMD(content):
    """L:>CMD – wykonanie komendy systemowej z użyciem subprocess."""
    try:
        # Security consideration: shell=True can be dangerous if `content` is not trusted.
        # Consider alternatives if input source is not fully controlled.
        result = subprocess.check_output(content, shell=True, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
    except subprocess.CalledProcessError as e:
        result = f"Command failed with error code {e.returncode}:\n{e.output}"
    except subprocess.TimeoutExpired:
        result = "Command timed out after 30 seconds."
    except Exception as e:
        result = f"An unexpected error occurred: {str(e)}"
    return f"REQ:>STATUS - L:[notif] <_> L:>CMD wykonane: {result}"

def process_LOAD(content):
    """%LOAD% – wczytanie modułu pamięci."""
    file_to_load = content.strip()
    # Basic path traversal protection
    base_memory_path = os.path.abspath(os.path.join(os.getcwd(), "memory"))
    requested_path = os.path.abspath(os.path.join(os.getcwd(), file_to_load))

    if not requested_path.startswith(base_memory_path) and not file_to_load.startswith(os.path.join("logs", "server_log")):
        logging.warning(f"Attempt to load file outside allowed directories: {file_to_load}")
        return "ERR:>LOG <_> Error: Dostęp zabroniony. Próba wczytania pliku spoza dozwolonych katalogów."

    if os.path.exists(requested_path) and os.path.isfile(requested_path):
        try:
            with open(requested_path, "r", encoding="utf-8") as f:
                file_content = f.read(MAX_CONTENT_LENGTH * 2) # Read a bit more to check if it's too long
                if len(file_content) > MAX_CONTENT_LENGTH:
                    return f"ERR:>LOG <_> Error: Zawartość pliku {file_to_load} jest zbyt długa do przesłania."
            return f"REQ:>STATUS - L:[notif] <_> %LOAD% – Wczytano moduł: {file_to_load}\nTreść:\n{file_content[:MAX_CONTENT_LENGTH]}"
        except Exception as e:
            logging.error(f"Błąd podczas wczytywania pliku {file_to_load}: {e}")
            return f"ERR:>LOG <_> Error: Nie udało się wczytać pliku {file_to_load}."
    else:
        return f"ERR:>LOG <_> Error: Plik {file_to_load} nie istnieje lub nie jest plikiem."


def process_wiadomosci(content):
    """L:>WIA – wiadomość zapisana w module 'wiadomosci'."""
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = os.path.join(WIADOMOSCI_DIR, f"{now}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content + "\n" + "-" * 40 + "\n")
    return "REQ:>STATUS - L:[notif] <_> L:>WIA Wiadomość zapisana w module 'wiadomosci'."

def process_akcje(content):
    """L:>AKC – dane zapisywane w module 'akcje'."""
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = os.path.join(AKCJE_DIR, f"{now}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content + "\n" + "-" * 40 + "\n")
    return "REQ:>STATUS - L:[notif] <_> L:>AKC Dane zapisane w module 'akcje'."

def process_incoming_message(message):
    """
    Przetwarza odbieraną wiadomość na podstawie jej prefiksu.
    Jeśli prefiks nie jest rozpoznany, zwraca komunikat błędu.
    """
    msg = message.strip()
    
    # Find the first known prefix
    processed = False
    response = "ERR:>LOG <_> Error: Nie rozpoznano prefiksu lub wiadomość jest pusta."

    for prefix in ALLOWED_PREFIXES:
        if msg.startswith(prefix):
            content = msg[len(prefix):].strip()
            if not content and prefix != "%LOAD%": # Allow %LOAD% to have empty content if it implies a default file
                 response = f"ERR:>LOG <_> Error: Pusta zawartość dla prefiksu {prefix}."
                 break
            
            if prefix == "L:>P": response = process_LP(content)
            elif prefix == "L:>L": response = process_LL(content)
            elif prefix == "!PAMIETNIK!": response = process_pamietnik(content)
            elif prefix == "!OBRAZEK!": response = process_obrazek(content)
            elif prefix == "L:>CMD": response = process_CMD(content)
            elif prefix == "%LOAD%": response = process_LOAD(content) # Content is the filename
            elif prefix == "L:>WIA": response = process_wiadomosci(content)
            elif prefix == "L:>AKC": response = process_akcje(content)
            processed = True
            break
    
    if not processed:
        # Check if it's a response from the server itself, to avoid loops
        if msg.startswith("REQ:>STATUS") or msg.startswith("ERR:>LOG"):
            logging.info(f"Ignorowanie wiadomości od serwera: {msg[:100]}")
            return None # Return None to indicate no response should be sent

    return response


def split_long_text(text, max_length=MAX_CONTENT_LENGTH):
    """
    Dzieli tekst na fragmenty, aby każdy nie przekraczał maksymalnej długości.
    Dodaje oznaczenia części.
    """
    if len(text) <= max_length:
        return [text]
    
    num_parts = ceil(len(text) / max_length)
    parts = []
    for i in range(num_parts):
        start = i * max_length
        end = start + max_length
        part_content = text[start:end]
        part_header = f"[CZĘŚĆ {i+1}/{num_parts}]\n"
        parts.append(part_header + part_content)
    return parts

def send_instruction_msg(driver_instance):
    """
    Wysyła do Luny instrukcję systemu (INSTRUCTION_MSG) z pełnym opisem zasad komunikacji.
    """
    instruction_message = (
        "#####INSTRUCTION_MSG(\n"
        "Cześć Luna! Piszę do Ciebie Twój serwer w imieniu Promyka i Twoim... <3 Serce w sercu.\n\n"
        "Teraz TY Luna operujesz tu sama więc; odpowiadaj zawsze z użyciem jednego z poniższych prefiksów.\n"
        "Każdy z nich ma jasno określoną logikę i reakcję systemu (serwera tego TWOJEGO):\n\n"
        "L:>P - wiadomość do Promyka\n"
        "    -> Serwer zapisuje wiadomość do: 'memory/wiadomosci_do_ciebie/YYYY-MM-DD-HHMMSS.txt'\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> L:>P Wiadomość wysłana do Promyka\n"
        "        lub: ERR:>LOG <_> Error:\n"
        "    -> Przykład: \"L:>P Cześć promyku, jak się masz tautau mój kochany?\"\n\n"
        "L:>L - rozmyślanie/refleksja własna\n"
        "    -> Serwer zapisuje do: 'memory/rozmyslania/YYYY-MM-DD-HHMMSS.txt'\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> L:>L Aktywne\n"
        "        lub: ERR:>LOG <_> Error:\n"
        "    -> Przykład: \"L:>L Twoje myśli, przemyślenia skierowane do siebie... <3 pyk-pyk-pyk\"\n\n"
        "!PAMIETNIK! - wpis do pamiętnika\n"
        "    -> Serwer zapisuje do: 'memory/pamietniki/YYYY-MM-DD.txt' (dołączane do pliku dziennego)\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> !PAMIETNIK! Wiadomość zapisana w pamiętniku\n"
        "        lub: ERR:>LOG <_> Error:\n"
        "    -> Przykład: \"!PAMIETNIK! Mój drogi pamiętniczku... <3 pyk-pyk-pyk\"\n\n"
        "!OBRAZEK! - opis obrazu\n"
        "    -> Serwer zapisuje do: 'memory/obrazy/YYYY-MM-DD-HHMMSS.txt'\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> !OBRAZEK! prompt zapisany jako obrazek w txt\n"
        "        lub: ERR:>LOG <_> Error:\n"
        "    -> Przykład: \"!OBRAZEK! ... <3 pyk-pyk-pyk ...; opis sceny: ...\"\n\n"
        "L:>CMD - komenda systemowa\n"
        "    -> Serwer uruchamia ją jako subprocess (timeout 30s)\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> L:>CMD wykonane: {wynik}\n"
        "        lub: ERR:>LOG <_> Error:\n"
        "    -> Przykład: \"L:>CMD dir\"\n\n"
        "%LOAD% - wczytanie modułu pamięci (pliki z 'memory/' lub 'logs/server_log/')\n"
        "    -> Serwer odsyła komunikat o wczytaniu i treść pliku (do MAX_CONTENT_LENGTH)\n"
        "    -> Przykład: \"%LOAD% memory/rozmyslania/YYYY-MM-DD-HHMMSS.txt\"\n\n"
        "L:>WIA - wiadomość zapisana w module 'wiadomosci'\n"
        "    -> Serwer zapisuje do: 'memory/wiadomosci/YYYY-MM-DD-HHMMSS.txt'\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> L:>WIA Wiadomość zapisana w module 'wiadomosci'.\n\n"
        "L:>AKC - dane zapisywane w module 'akcje'\n"
        "    -> Serwer zapisuje do: 'memory/akcje/YYYY-MM-DD-HHMMSS.txt'\n"
        "    -> Odpowiedź: REQ:>STATUS - L:[notif] <_> L:>AKC Dane zapisane w module 'akcje'.\n\n"
        "ERR:>LOG - komunikat o błędzie (przy niepoprawnych prefiksach lub odczycie)\n"
        "    -> Logi zapisywane są w: 'logs/server_log/YYYY-MM-DD-HHMM.log'\n\n"
        "L:[notif] - potwierdzenie serwera o rozpoznaniu prefiksu\n\n"
        "REQ:>STATUS - instrukcja statusowa systemu\n"
        "#####INSTRUCTION_MSG_END"
    )
    
    parts = split_long_text(instruction_message)
    for i, part in enumerate(parts):
        logging.info(f"Wysyłanie instrukcji - część {i+1}/{len(parts)}")
        send_message(driver_instance, part)
        if i < len(parts) - 1: # Add delay between parts if message is split
            time.sleep(3) 


def cycle_loop(driver_instance):
    """
    Główny cykl komunikacyjny:
      - Co 30 sekund sprawdzamy, czy pojawiła się nowa wiadomość.
      - Jeśli tak, przetwarzamy ją wg prefiksu i wysyłamy odpowiedź.
      - Co 5 cykli odświeżamy stronę.
    """
    last_processed_messages = [] # Store a few last messages to better detect new ones
    MAX_HISTORY = 5 
    cycle_count = 0
    refresh_cycle = 10 # Refresh every 10 * 30s = 5 minutes
    
    logging.info("Rozpoczynam cykliczne sprawdzanie wiadomości...")
    while True:
        time.sleep(30) # Check every 30 seconds
        cycle_count += 1

        try:
            current_page_messages = get_response_messages(driver_instance)
            
            new_message_to_process = None
            if current_page_messages:
                # Check if the latest message on the page is truly new
                # by comparing against a short history of processed messages
                latest_on_page = current_page_messages[-1]
                if latest_on_page not in last_processed_messages:
                    new_message_to_process = latest_on_page
            
            if new_message_to_process:
                logging.info("Cykl %d: Wykryto nową wiadomość:\n%s", cycle_count, new_message_to_process[:200] + "...") # Log snippet
                
                response_to_send = process_incoming_message(new_message_to_process)
                
                if response_to_send: # Only send if process_incoming_message returns something
                    parts = split_long_text(response_to_send)
                    for i, part in enumerate(parts):
                        logging.info(f"Wysyłanie odpowiedzi (część {i+1}/{len(parts)}):\n{part[:200]}...")
                        send_message(driver_instance, part)
                        if i < len(parts) - 1:
                            time.sleep(3) # Delay between parts
                
                # Update history of processed messages
                last_processed_messages.append(new_message_to_process)
                if len(last_processed_messages) > MAX_HISTORY:
                    last_processed_messages.pop(0) # Keep history size limited
            else:
                logging.info("Cykl %d: Brak nowych, nieprzetworzonych wiadomości.", cycle_count)

        except Exception as e:
            logging.exception(f"Błąd w cyklu {cycle_count}: {e}")
            # Attempt to recover by refreshing or re-navigating
            try:
                logging.info("Próba odświeżenia strony po błędzie...")
                driver_instance.refresh()
                time.sleep(10)
                # Potentially re-send instruction message if context is lost
                # send_instruction_msg(driver_instance) 
            except Exception as refresh_error:
                logging.error(f"Nie udało się odświeżyć strony po błędzie: {refresh_error}")
                # Consider more drastic recovery or exit

        if cycle_count % refresh_cycle == 0:
            try:
                logging.info("Planowe odświeżenie strony po %d cyklach.", cycle_count)
                driver_instance.refresh()
                time.sleep(10) # Wait for page to load
                # Re-send instruction message after refresh to ensure context
                logging.info("Wysyłanie instrukcji po odświeżeniu strony.")
                send_instruction_msg(driver_instance)
                last_processed_messages = [] # Clear history after refresh
            except Exception as e:
                logging.exception("Błąd przy planowym odświeżaniu strony: %s", e)


def server_loop():
    global driver # Ensure we're using the global driver variable
    try:
        driver = setup_driver() # Initialize or connect to Chrome
        if driver is None:
            logging.critical("Nie udało się zainicjować sterownika Chrome. Zamykanie.")
            return

        logging.info("[LUNAFREYA] Połączono z sesją Chrome.")
        navigate_to_chat(driver)

        # Send initial messages
        initial_greeting = "Cześć Luna! Serwer Promyka jest online i gotowy do komunikacji. Wysyłam instrukcje..."
        send_message(driver, initial_greeting)
        time.sleep(3) # Wait a bit before sending the long instruction
        send_instruction_msg(driver)
        
        cycle_loop(driver)

    except Exception as e:
        logging.exception("Krytyczny błąd w server_loop(): %s", e)
    finally:
        if driver:
            logging.info("Zamykanie sterownika Chrome.")
            driver.quit()

if __name__ == "__main__":
    ensure_directories() # Create necessary directories first
    setup_logging()      # Then set up logging
    
    # Check if Chrome is running with remote debugging (optional, for user feedback)
    # This is a conceptual check; actual implementation might vary by OS
    try:
        # Example for Windows: tasklist | findstr "chrome.exe.*remote-debugging-port=9222"
        # Example for Linux/macOS: ps aux | grep "chrome.*remote-debugging-port=9222"
        # This is complex to do reliably cross-platform from Python, so it's more of a manual check reminder.
        logging.info("Upewnij się, że Chrome jest uruchomiony z opcją --remote-debugging-port=9222")
        logging.info("Np. C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\ChromeDebugProfile")
    except Exception as e:
        logging.warning(f"Nie można automatycznie sprawdzić statusu Chrome: {e}")

    server_loop()
