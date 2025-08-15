import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load the Titanic dataset
df = sns.load_dataset('titanic')

# EDA
print("First five rows of the dataset:")
print(df.head())

print("Last five rows of the dataset:")
print(df.tail())

# Summary statistics
print("Summary statistics of the dataset:")
print(df.describe())

print("Concise summary of the dataframe (including data types and non-null counts):")
print(df.info())

# Value Counts
print("\nDistribution of passenger classes:")
print(df['class'].value_counts())

# Missing Values Analysis
print("\nPercentage of missing values in each column:")
print(df.isnull().sum() / len(df) * 100)