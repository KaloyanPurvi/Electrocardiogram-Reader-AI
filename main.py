
import heartpy as hp
import neurokit2 as nk
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
import numpy as np
from tkinter import filedialog, messagebox, Toplevel, Text, Scrollbar
from tkinter.ttk import Treeview
import openai  #AI за диагностика

# Референтни стойности за ЕКГ параметри
REFERENCE_VALUES = {
    "bpm": "60-100",
    "ibi": "600-1000 ms",
    "sdnn": "20-50 ms",
    "sdsd": "10-50 ms",
    "rmssd": "20-50 ms",
    "pnn20": "> 0.2",
    "pnn50": "> 0.05",
    "hr_mad": "10-30",
    "sd1": "10-50 ms",
    "sd2": "20-80 ms",
    "s": "Varies",
    "sd1/sd2": "0.5-1.5"
}


OPENAI_API_KEY  = "INPUT REAL API KEY"


def getAiDiagnosis(ekgResults, symptoms): #Функцията изпраща заявка към openAI за възможни диагнози въз основа на резултатите от ЕКГ и симптомите 
    
    if not ekgResults:
        return "Няма налични ЕКГ данни за диагностика"
    
    prompt = f"""
    Пациента има следните ЕКГ резултати: {ekgResults}.
    Освен това съобщава следните симптоми: {symptoms}.
    Въз основа на тези данни, какви са възможните медицински състояния?
    Дай кратък списък с обяснения и кой екг резултат води до това съмнение. В краят на цялата диагностика отбележи "Моля, обсъдете с вашия лекар."
    """
    
  
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response= client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def analyzeWithNeurokit(ekgData, Hz): #R вални
    signals, info = nk.ecg_process(ekgData, Hz)
    return info if isinstance(info, dict) else {}
   

def analyzeWithHeartpy(ekgData, Hz): #HRV, BPM
    wd, measures = hp.process(ekgData, Hz)
    return wd, measures
   

def preprocessEKG(data, Hz): #Предварителна обработка на ЕКГ данните с Neurokit2
    return nk.ecg_clean(data, Hz)

def openFile():             #Отваряме файлов прозорец за избор на файл с ЕКГ данни
    filePath = filedialog.askopenfilename(title="Изберете файл с ЕКГ данни", filetypes=[("CSV Files", "*.csv")])
    if filePath:
        try:
            global ekgData, timeData
            ekgData = pd.read_csv(filePath)
            timeData = pd.Series(range(len(ekgData)))
        except Exception as e:
            messagebox.showerror("Грешка", f"Неуспешно зареждане на файл: {e}")

def showResultsTable(results, symptoms):#Показваме резултатите от анализа в таблица заедно с диагнозата на изк. интелект
    resultWindow = Toplevel(root)
    resultWindow.title("Резултати от ЕКГ анализа")
    
    tree = Treeview(resultWindow, columns=("Параметър", "Стойност", "Референтна стойност"), show="headings")
    tree.heading("Параметър", text="Измерване")
    tree.heading("Стойност", text="Резултат")
    tree.heading("Референтна стойност", text="Референтни стойности")
    
   # i=0
    for key, value in results.items():
       # i+=1
       # if i > 12:  
       #     break 
        if isinstance(value, (list, tuple, np.ndarray)):  
            fixedData = pd.Series(np.array(value).flatten()).dropna()#Превръщаме в масив и премахваме NaN
            if not fixedData.empty:  
                roundedValue = round(fixedData.median(), 4) #Изчисляваме ср. стойност
            else:
             roundedValue = "N/A"
        else:
         try:
          roundedValue = round(float(value), 4) if isinstance(value, (int, float)) else value
         except:
          roundedValue = "N/A"


        reference = REFERENCE_VALUES.get(key, "...")
        tree.insert("", tk.END, values=(key, roundedValue, reference))
    
    tree.pack(expand=True, fill=tk.BOTH)
    
    diagnosisText = getAiDiagnosis(results, symptoms)
    diagLabel = tk.Label(resultWindow, text="Възможни диагнози:", font=("Arial", 12,"bold"))
    diagLabel.pack(pady=5)
    diagBox = Text(resultWindow, height=8, wrap=tk.WORD)
    diagBox.insert(tk.END, diagnosisText)
    diagBox.pack(expand=True, fill=tk.BOTH)

def visualizeEkg(time, data, title="ЕКГ СИГНАЛ"):

    plt.figure(figsize=(10, 4))
    plt.plot(time, data, label="EKG Signal")
    plt.title(title)
    plt.xlabel("Time (samples)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid()
    plt.show()

def startAnalysis():
    samplingRate = 300  
    if 'ekgData' not in globals():
        messagebox.showerror("Грешка","Не е зареден файл. Моля, заредете ЕКГ файл първо!")
        return
    
    symptoms = symptomInput.get()
    rawSignal = ekgData.iloc[:, 1]  
    
    cleanedSignal = preprocessEKG(rawSignal, samplingRate)
    visualizeEkg(timeData, cleanedSignal, title="Cleaned EKG Signal")
    #Анализ
    _, heartpyMeasures = analyzeWithHeartpy(cleanedSignal, samplingRate)
    neurokitResults = analyzeWithNeurokit(cleanedSignal, samplingRate)
    
    resultsData = {}
    if heartpyMeasures:
        resultsData.update(heartpyMeasures)
    if neurokitResults:
        resultsData.update(neurokitResults)
    
    if resultsData:
        showResultsTable(resultsData, symptoms)
    else:
        messagebox.showinfo("Завършено", "Няма данни")

#main
root = tk.Tk()
root.title("ЕКГ ДИАГНОСТИКА")
root.resizable(False, False)

symptomLabel = tk.Label(root, text="Въведете симптоми:")
symptomLabel.pack()
symptomInput = tk.Entry(root, width=50)
symptomInput.pack(pady=5)

btnLoad = tk.Button(root, text="ЕКГ файл", command=openFile, width=20)
btnLoad.pack(pady=10)
btnAnalyze = tk.Button(root, text="Анализ", command=startAnalysis, width=20)
btnAnalyze.pack(pady=10)

root.mainloop()