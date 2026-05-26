import tkinter as tk
from tkinter import messagebox, scrolledtext
from requests import options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading
import time
import random
import string

class SlimStampenBotV2:
    def __init__(self):
        self.driver = None
        self.translation_dict = {}
        self.is_running = False
        
        # Setup GUI
        self.root = tk.Tk()
        self.root.title("SlimStampen Bot Ultimate v2")
        self.root.geometry("380x800")
        self.root.attributes("-topmost", True)
        
        # Knoppen
        tk.Label(self.root, text="--- Controle ---", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(self.root, text="1. Open Site & Log in", command=self.open_browser, width=30).pack(pady=2)
        tk.Button(self.root, text="2. 🔥 START AUTO-PILOT", command=self.start_auto_pilot, width=30, bg="green", fg="white").pack(pady=10)
        
        # Handmatige knoppen voor noodgevallen
        tk.Button(self.root, text="Sla Woordenlijst Op", command=self.scrape_words, width=25).pack(pady=2)
        tk.Button(self.root, text="Start/Stop Invullen", command=self.toggle_bot, width=25, bg="orange").pack(pady=2)

        # Sliders voor menselijke instellingen
        tk.Label(self.root, text="--- Menselijke Instellingen ---", font=("Arial", 10, "bold")).pack(pady=10)
        self.reaction_slider = tk.Scale(self.root, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, label="Reactietijd (sec)")
        self.reaction_slider.set(0.8)
        self.reaction_slider.pack()
        

        
        self.typo_slider = tk.Scale(self.root, from_=0, to=50, orient=tk.HORIZONTAL, label="% Kans op typfout")
        self.typo_slider.set(5)
        self.typo_slider.pack()
        
        self.wrong_word_slider = tk.Scale(self.root, from_=0, to=100, orient=tk.HORIZONTAL, label="% Foutpercentage")
        self.wrong_word_slider.set(2)
        self.wrong_word_slider.pack()

    def open_browser(self):
        options = Options()
        options.add_experimental_option("detach", True)
        self.driver = webdriver.Chrome(options=options)  # Geen Service() nodig
        self.driver.get("https://metis.slimstampen.nl")

    def scrape_words(self):
        if not self.driver: return
        script = """
        let dict = {};
        document.querySelectorAll('ion-item').forEach(item => {
            const cols = item.querySelectorAll('ion-col');
            if (cols.length === 2) {
                const dutchRaw = cols[0].querySelector('ion-text')?.textContent?.trim();
                const english = cols[1].querySelector('ion-text')?.textContent?.trim();
                if (dutchRaw && english) {
                    dutchRaw.split(',').map(w => w.trim()).forEach(word => { dict[word] = english; });
                }
            }
        });
        return dict;
        """
        new_words = self.driver.execute_script(script)
        self.translation_dict.update(new_words)
        print(f"Systeem: {len(new_words)} woorden geleerd.")

    def start_auto_pilot(self):
        """Start de analyse in een aparte thread zodat de GUI niet vastloopt"""
        threading.Thread(target=self.deep_check_and_solve, daemon=True).start()

    def deep_check_and_solve(self):
        if not self.driver:
            messagebox.showwarning("Fout", "Open eerst de browser!")
            return

        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'ion-card[data-test="lesson-card"]')
            for i in range(len(cards)):
                current_cards = self.driver.find_elements(By.CSS_SELECTOR, 'ion-card[data-test="lesson-card"]')
                card = current_cards[i]
                
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                time.sleep(random.uniform(0.3, 0.7))

                # Check of er nog kroontjes te halen zijn
                unearned = self.driver.execute_script("return arguments[0].querySelectorAll('ion-icon[name=\"crown\"].ion-color-grey').length;", card)
                
                if unearned == 0:
                    continue

                # Klik op de kaart
                self.driver.execute_script("arguments[0].click();", card)
                time.sleep(random.uniform(2, 3))

                # Check of het voor vandaag al klaar is (timeLock)
                is_done_today = self.driver.execute_script("""
                    let lockElem = document.getElementById('timeLockVisible');
                    if (lockElem && lockElem.offsetParent !== null) {
                        let text = lockElem.innerText.toLowerCase();
                        // Hij blokkeert nu op 'tot morgen', 'nog ... uur' en 'nog ... minuten'
                        return text.includes('tot morgen') || 
                            text.includes('nog') || 
                            text.includes('uur') || 
                            text.includes('minut'); 
                    }
                    return false;
                """)

                if is_done_today:
                    print("Lijst al gedaan voor vandaag. Volgende...")
                    self.driver.back()
                    time.sleep(random.uniform(1, 3))
                    continue

                # --- HIER IS DE LIJST ACTIEF EN NIET GEDAAN ---
                # Zoek de 'Start' knop die je stuurde
                start_buttons = self.driver.find_elements(By.XPATH, "//ion-button[contains(., 'Start')]")
                if start_buttons:
                    start_buttons[0].click()
                    print("Op 'Start' geklikt. Bot activeren...")
                    time.sleep(random.uniform(1, 3))
                    
                    # Woorden leren en de bot starten
                    self.scrape_words()
                    self.is_running = True
                    self.bot_loop() # Dit blokkeert tot de lijst klaar is (door de break in bot_loop)
                    
                    # Als de bot_loop klaar is, gaat hij hier verder naar de volgende kaart
                    time.sleep(random.uniform(1, 3))
                else:
                    self.driver.back()
                    time.sleep(random.uniform(1, 3))

            messagebox.showinfo("Klaar", "Alle beschikbare lijsten voor vandaag zijn gecontroleerd!")

        except Exception as e:
            print(f"Fout in Auto-Pilot: {e}")

    def toggle_bot(self):
        self.is_running = not self.is_running
        if self.is_running:
            threading.Thread(target=self.bot_loop, daemon=True).start()

    def bot_loop(self):
        """De kern-loop die de vragen beantwoordt"""
        while self.is_running:
            try:
                # 1. Check Einde
                finish_button = self.driver.find_elements(By.CSS_SELECTOR, "ion-button[data-test='return-to-lesson']")
                if finish_button and finish_button[0].is_displayed():
                    time.sleep(self.reaction_slider.get() + random.uniform(0, 0.4))
                    finish_button[0].click()
                    self.translation_dict = {}
                    self.is_running = False
                    print("Sessie afgerond.")
                    return # Belangrijk: stop de functie zodat deep_check verder kan

                # 2. Check Tussenpagina's (Next / Ik ken het)
                continue_selectors = ["ion-button[data-test='next-button']", "ion-button[data-test='register-study-trial']"]
                button_found = False
                for selector in continue_selectors:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if btns and btns[0].is_displayed():
                        time.sleep(self.reaction_slider.get() + random.uniform(0, 0.4))
                        btns[0].click()
                        button_found = True; break
                if button_found: continue

                # 3. Invullen
                
                cue_text = self.driver.find_element(By.ID, "cue-text").text.strip().lower()
                answer = None

                for nl, en in self.translation_dict.items():
                    if nl.lower() == cue_text:
                        answer = en
                        break
                if not answer:
                    for nl, en in self.translation_dict.items():
                        if nl.lower() in cue_text or cue_text in nl.lower():
                            answer = en
                            break
                if answer:
                    target = answer
                    # Fout-percentage logica
                    if random.randint(1, 100) <= self.wrong_word_slider.get() and len(self.translation_dict) > 1:
                        alt = [v for v in self.translation_dict.values() if v != answer]
                        if alt: target = random.choice(alt)

                    time.sleep(self.reaction_slider.get() + random.uniform(0, 0.4))
                    inp = self.driver.find_element(By.CSS_SELECTOR, 'input.native-input')
                    inp.clear()

                    for char in target:
                        if random.randint(1, 100) <= self.typo_slider.get():
                            inp.send_keys(random.choice(string.ascii_lowercase))
                            time.sleep(random.uniform(0.05, 0.2)); inp.send_keys(Keys.BACKSPACE)
                        inp.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.1))

                    time.sleep(random.uniform(0.4, 0.6))
                    inp.send_keys(Keys.ENTER)
                    time.sleep(random.uniform(1.05, 1.95))
            except:
                time.sleep(random.uniform(0.8, 1.5))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    bot = SlimStampenBotV2()
    bot.run()