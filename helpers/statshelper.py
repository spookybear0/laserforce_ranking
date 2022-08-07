from typing import List, Tuple
import matplotlib.pyplot as plt
from PIL import Image
import seaborn as sns
import pandas as pd
import PIL

dark_mode = {"ytick.color" : "w",
            "xtick.color" : "w",
            "axes.labelcolor" : "w",
            "axes.edgecolor" : "w",
            "axes.titlecolor": "w"
}

def clear_plt():
    fig = plt.figure()
    plt.figure().clear()
    plt.close()
    plt.cla()
    plt.clf()

def lineplot(data: Tuple[List[int]], title: str="", xlabel: str="", ylabel: str="", *args, **kwargs) -> Image.Image:
    plt.style.use("dark_background")
    fig = sns.regplot(*data, ci=None, *args, **kwargs).figure

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    fig.canvas.draw()

    img = PIL.Image.frombytes("RGB", fig.canvas.get_width_height(), fig.canvas.tostring_rgb())

    clear_plt()
    return img

def barplot(labels: List[str], data: List[int], title: str="", xlabel: str="", ylabel: str="", *args, **kwargs):
    plt.rcParams.update(dark_mode)
    plot = sns.barplot(x=labels, y=data, *args, **kwargs)
    fig = plot.figure

    plot.set_facecolor("#121212")
    fig.patch.set_facecolor("#1A1A1A")
    
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    fig.canvas.draw()

    img = PIL.Image.frombytes("RGB", fig.canvas.get_width_height(), fig.canvas.tostring_rgb())

    clear_plt()
    return img