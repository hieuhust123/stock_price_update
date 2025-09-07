# import pandas as pd
# from sklearn.model_selection import train_test_split



# # Load data
# df = pd.read_csv(r"C:\Users\Hieu dai ca'\Downloads\Iris.csv")

# # Remove Id column if present
# if 'Id' in df.columns:
#     df = df.drop(columns=['Id'])

# # Separate features and labels
# X = df.drop(columns=['Species']).values
# Y = df['Species'].values

# # Encode labels as integers (optional, for ML use; else keep as string)
# # from sklearn.preprocessing import LabelEncoder
# # le = LabelEncoder()
# # Y = le.fit_transform(Y)

# # Split
# X_train, X_test, Y_train, Y_test = train_test_split(
#     X, Y, test_size=0.3, random_state=42, stratify=Y
# )

# # Write .dat files
# def save_dat(filename, array):
#     with open(filename, "w") as f:
#         for row in array:
#             if isinstance(row, (list, tuple, pd.Series, pd.DataFrame)):
#                 row = list(row)
#             f.write(",".join(str(x) for x in row) + "\n")

# save_dat("trainX.dat", X_train)
# save_dat("testX.dat", X_test)
# save_dat("trainY.dat", [[y] for y in Y_train])
# save_dat("testY.dat", [[y] for y in Y_test])

# print("Files written: trainX.dat, testX.dat, trainY.dat, testY.dat")


import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Load the data
df = pd.read_csv(r"C:\Users\Hieu dai ca'\Downloads\Iris.csv")
# Map species to integers
label_map = {'setosa': 0, 'versicolor': 1, 'virginica': 2}
df['species'] = df['species'].map(label_map)

# Split into train and test sets (70% train, 30% test)
train_df, test_df = train_test_split(df, test_size=0.3, random_state=42, stratify=df['species'])

# Save features
train_df.iloc[:, 0:4].to_csv(r'D:\read_journal\toy_dataset_with_label\trainX.dat', index=False, header=False)
test_df.iloc[:, 0:4].to_csv(r'D:\read_journal\toy_dataset_with_label\testX.dat', index=False, header=False)

# One-hot encode labels for train
train_labels = train_df['species'].values.astype(int)
train_one_hot = np.zeros((train_labels.size, 3))
train_one_hot[np.arange(train_labels.size), train_labels] = 1
np.savetxt(r'D:\read_journal\toy_dataset_with_label\trainY.dat', train_one_hot, delimiter=',')

# One-hot encode labels for test
test_labels = test_df['species'].values.astype(int)
test_one_hot = np.zeros((test_labels.size, 3))
test_one_hot[np.arange(test_labels.size), test_labels] = 1
np.savetxt(r'D:\read_journal\toy_dataset_with_label\testY.dat', test_one_hot, delimiter=',')