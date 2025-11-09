import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
import random
import tkinter as tk
from tkinter import filedialog, messagebox

class Gsmarena:
    def __init__(self, input_file_path):
        self.devices = []
        self.features = ["Brand", "Model Name", "Model Image"]
        self.url = 'https://www.gsmarena.com/'
        self.input_file_path = input_file_path
        self.updated_devices = []

    def crawl_html_page(self, sub_url):
        url = self.url + sub_url
        headers = {"User-Agent": "Mozilla/5.0"}
        retries = 5
        while retries > 0:
            try:
                time.sleep(random.uniform(5, 10)) 
                page = requests.get(url, timeout=10, headers=headers)
                if page.status_code == 429:
                    print("Too many requests. Retrying after a delay...")
                    time.sleep(60)
                    retries -= 1
                    continue
                return BeautifulSoup(page.text, 'html.parser')
            except requests.ConnectionError:
                print("Network error. Please check your connection and try again.")
                exit()
            except Exception as e:
                print(f"An error occurred: {e}")
                exit()
        return None

    def get_devices_by_year(self, year):
        base_url = f"https://www.gsmarena.com/results.php3?nYearMin={year}&nYearMax={year}&sSIMTypes=4"
        soup = self.crawl_html_page(f'results.php3?nYearMin={year}&nYearMax={year}')

        if soup is None:
            print("Failed to retrieve HTML content from GSMArena.")
            return []

        devices = []
        for device in soup.find_all('div', class_='makers'):
            links = device.find_all('a')
            for link in links:
                device_name = link.text
                device_url = "https://www.gsmarena.com/" + link.get('href')
                devices.append((device_name, device_url))

        return devices

    def get_device_specifications(self, device_url):
        soup = self.crawl_html_page(device_url)
        if soup is None:
            return {}

        phone_data = {}
        model_name_tag = soup.find('h1', class_='specs-phone-name-title')
        if model_name_tag:
            model_name = model_name_tag.text.strip()
        else:
            print(f"No model name found for specification link: {device_url}")
            return {}

        model_img_div = soup.find('div', class_='specs-photo-main')
        if model_img_div:
            model_img_tag = model_img_div.find('img')
            if model_img_tag:
                model_img = model_img_tag['src']
            else:
                model_img = 'N/A'
        else:
            model_img = 'N/A'

        phone_data.update({"Brand": model_name.split()[0]})
        phone_data.update({"Model Name": model_name})
        phone_data.update({"Model Image": model_img})

        supports_esim = False 
        for table in soup.findAll('table'):
            for line in table.findAll('tr'):
                temp = []
                for l in line.findAll('td'):
                    text = l.getText().strip()
                    temp.append(text)
                if temp:
                    key = temp[0]
                    value = temp[1]
                    if key in phone_data:
                        key += '_1'
                    if key not in self.features:
                        self.features.append(key)

                    phone_data[key] = value

                    if 'SIM' in key and 'eSIM' in value:
                        supports_esim = True
        return phone_data if supports_esim else {}

    def incremental_update(self, absolute_path):
        current_year = datetime.now().year
        existing_devices_df = self.read_existing_devices()
        existing_device_names = set(existing_devices_df['Model Name'].str.replace(" ", "").values)

        new_devices = self.get_devices_by_year(current_year)

        for device_name, device_url in new_devices:
            normalized_device_name = device_name.replace(" ", "")
            if normalized_device_name not in existing_device_names:
                print(f"Fetching specs for new device: {device_name}")
                specs = self.get_device_specifications(device_url)
                if specs:
                    self.updated_devices.append(specs)
            else:
                print(f"Device already exists: {device_name}")

            time.sleep(1)

        if self.updated_devices:
            updated_devices_df = pd.DataFrame(self.updated_devices)
            updated_devices_df = updated_devices_df.reindex(columns=existing_devices_df.columns, fill_value="")

            all_devices_df = pd.concat([existing_devices_df, updated_devices_df], ignore_index=True)
            output_file_name = datetime.now().strftime("%d%m%y") + "_GSMArena_eSIM_Devices.csv"
            output_file_path = os.path.join(absolute_path, output_file_name)
            all_devices_df.to_csv(output_file_path, index=False)
            print(f"File '{output_file_path}' successfully created and updated.")
        else:
            print("No new devices found or updated.")

    def read_existing_devices(self):
        try:
            devices_df = pd.read_csv(self.input_file_path)
            return devices_df
        except Exception as e:
            print(f"Error reading file: {e}")
            return pd.DataFrame()

def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        entry_file_path.delete(0, tk.END)
        entry_file_path.insert(0, file_path)

def submit_file():
    file_path = entry_file_path.get()
    if not file_path:
        messagebox.showerror("Error", "Please select a file.")
        return

    absolute_path = os.path.dirname(file_path)
    print(f"Absolute Path: {absolute_path}")

    status_label.config(text="Fetching data... Please wait")
    root.update()

    gsmarena = Gsmarena(file_path)
    gsmarena.incremental_update(absolute_path)

    if gsmarena.updated_devices:
        output_message = f"The incremental update process is complete!\nFile saved in: {absolute_path}"
    else:
        output_message = "No new devices found or updated."

    status_label.config(text="")
    messagebox.showinfo("Finished", output_message)

root = tk.Tk()
root.title("GSMArena Incremental Update")

frame_file = tk.Frame(root)
frame_file.pack(padx=10, pady=10)
label_file_path = tk.Label(frame_file, text="Select Input File:")
label_file_path.pack(side=tk.LEFT)
entry_file_path = tk.Entry(frame_file, width=50)
entry_file_path.pack(side=tk.LEFT)

button_browse = tk.Button(frame_file, text="Browse", command=browse_file)
button_browse.pack(side=tk.LEFT)

status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=10)

button_submit = tk.Button(root, text="Submit", command=submit_file)
button_submit.pack(pady=20)

root.mainloop()