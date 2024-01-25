import torch
import pandas as pd
import numpy as np
import sys
sys.path.append('.')
import os
sys.path.append('./scripts')
from scripts import load_dataset
import sklearn.model_selection
import ast
from sklearn.metrics.pairwise import cosine_similarity

def calculate_distances(embedding_str):
    start = embedding_str.find('[[')
    end = embedding_str.find(']]')+2
    embedding_str = embedding_str[start:end]
    image_embedding = torch.tensor(ast.literal_eval(embedding_str))
    image_embedding_values = np.array(image_embedding.flatten().tolist()).reshape(1, -1)

    prompt_distances = []
    # Reshape the vectors to be 2D arrays for sklearn's cosine_similarity
    #image_embedding = image_embedding.reshape(1, -1)
    for prompt_embedding in prompt_embeddings:
        prompt_embedding_values = np.array(prompt_embedding.flatten().tolist()).reshape(1, -1)
        # Calculate Cosine Similarity         
        prompt_distances.append(cosine_similarity(image_embedding_values, prompt_embedding_values)[0,0])

    model_input = np.concatenate((image_embedding_values[0], np.array(prompt_distances))).astype(np.float32)
    return model_input.tobytes()

def balance_data(max_num, unbalanced_df, country_list):
    balanced_array = []
    for index,row in country_list.iterrows():
        country_df = unbalanced_df.loc[unbalanced_df["label"] == row["Country"]]
        country_samples_count = len(country_df.index)
        if country_samples_count > max_num:
            drop_indices = np.random.choice(country_df.index,country_samples_count-max_num, replace=False)
            replace_df = country_df.drop(drop_indices)
            balanced_array.append(replace_df)
        else:
            balanced_array.append(country_df)
    balanced_df = pd.concat(balanced_array, ignore_index=True)
    return balanced_df

def save_embeddings(path, name, dataframe):
    dataframe.to_csv(f"{path}/{name}.csv", index=False)

def save_batches(path, name, dataframe):
    batch_size = 1000
    num_batches = len(dataframe) // batch_size

    # Iterate over the DataFrame in batches
    for i in range(num_batches + 1):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(dataframe))
        
        batch_df = dataframe.iloc[start_idx:end_idx]
                
        # Save or process the batch as needed
        batch_df.to_csv(f"{path}/{name}_{i}.csv", index=False)






# Embeddings of Prompt
prompt_embeddings = torch.load('./Embeddings/Prompt/prompt_image_shows_embedding.pt')

# Directory containing CSV files
directory = '/home/kieran/Documents/Uni/WiSe23-24/Good_Practices_of_Machine_Learning/good_practices_ml/Embeddings/Image'

# Get a list of filenames that start with "geoguessr" and end with ".csv"
geoguessr_file_list = [file for file in os.listdir(directory) if file.startswith('geoguessr') and file.endswith('.csv')]
tourist_df = pd.read_csv('/home/kieran/Documents/Uni/WiSe23-24/Good_Practices_of_Machine_Learning/good_practices_ml/Embeddings/Image/bigfoto_embeddings.csv')
aerial_df = pd.read_csv('/home/kieran/Documents/Uni/WiSe23-24/Good_Practices_of_Machine_Learning/good_practices_ml/Embeddings/Image/aerial_map_embeddings.csv')
print('loaded databases')

# Initialize an empty list to store DataFrames
dfs = []

# Iterate through the files, read them as DataFrames, and append to the list
for file in geoguessr_file_list:
    file_path = os.path.join(directory, file)
    df = pd.read_csv(file_path)
    dfs.append(df)
print('combined geoguessr databases')

# Concatenate all DataFrames in the list into a single DataFrame
combined_df = pd.concat(dfs, ignore_index=True)

# Calculate distances of all aerial samples
aerial_distances = []
for index, row in aerial_df.iterrows():
    aerial_distances.append(calculate_distances(row['Embedding']))

aerial_df['model_input'] = aerial_distances
model_input_aerial_df = aerial_df.drop(columns=["Embedding"])
print('calculated aerial distances')


# Calculate distances of all geoguessr samples
geoguessr_distances = []
for index, row in combined_df.iterrows():
    geoguessr_distances.append(calculate_distances(row['Embedding']))
    if index % 50 == 0:
        print(f'{index} distances calculated')

combined_df['model_input'] = geoguessr_distances
model_input_combined_df = combined_df.drop(columns=["Embedding"])
print('calculated geoguessr distances')


# Calculate distances of all tourist samples
tourist_distances = []
for index, row in tourist_df.iterrows():
    tourist_distances.append(calculate_distances(row['Embedding']))

tourist_df['model_input'] = tourist_distances
model_input_tourist_df = tourist_df.drop(columns=["Embedding"])
print('calculated tourist distances')





country_list = pd.read_csv("/home/kieran/Documents/Uni/WiSe23-24/Good_Practices_of_Machine_Learning/good_practices_ml/data_finding/country_list.csv")

# Create Balanced Dataset
balanced_df = balance_data(max_num=2000,country_list=country_list, unbalanced_df=combined_df)
remainder_df = pd.concat([combined_df, balanced_df], ignore_index=True).drop_duplicates(keep=False)

# Remove 15% of this Dataset for Testing
balanced_train_and_val, balanced_test = sklearn.model_selection.train_test_split(balanced_df, test_size=0.15, random_state=1234, shuffle=True)

# Add the 85% Balanced Training back to the remaining Unbalanced Geoguessr
unbalanced_df = pd.concat([remainder_df,balanced_train_and_val], ignore_index=True, sort=False)

# Randomly select the same amount of 'training samples' from this Unbalanced Dataset
remove_number = len(remainder_df.index)
drop_indices = np.random.choice(unbalanced_df.index, remove_number, replace=False)
unbalanced_train_and_val = unbalanced_df.drop(drop_indices)
assert(len(unbalanced_train_and_val.index) == len(balanced_train_and_val.index))

# Remove 15% of Aerial Images and Tourist Images for Testing
aerial_train_and_val, aerial_test = sklearn.model_selection.train_test_split(aerial_df, test_size=0.15, random_state=1234, shuffle=True)
tourist_train_and_val, tourist_test = sklearn.model_selection.train_test_split(tourist_df, test_size=0.15, random_state=1234, shuffle=True)

# todo TOURIST_TRAIN AND AERIAL_TRAIN MAY BE TOO BIG/SMALL
replace_tourist_number = len(tourist_train_and_val.index)
replace_aerial_number = len(aerial_train_and_val.index)
replace_number = replace_tourist_number + replace_aerial_number
drop_indices = np.random.choice(balanced_train_and_val.index, replace_number, replace=False)
replace_df = balanced_train_and_val.drop(drop_indices)
replace_train_and_val = pd.concat([replace_df,tourist_train_and_val, aerial_train_and_val], ignore_index=True, sort=False)
assert(len(replace_train_and_val.index) == len(balanced_train_and_val.index))

# Split validation from training for each database
balanced_train, balanced_val = sklearn.model_selection.train_test_split(balanced_train_and_val, test_size=0.15, random_state=1234, shuffle=True)
unbalanced_train, unbalanced_val = sklearn.model_selection.train_test_split(unbalanced_train_and_val, test_size=0.15, random_state=1234, shuffle=True)
replace_train, replace_val = sklearn.model_selection.train_test_split(replace_train_and_val, test_size=0.15, random_state=1234, shuffle=True)

#Save Training Embeddings
save_batches('./Embeddings/Training/Balanced','balanced', balanced_train)
save_batches('./Embeddings/Training/Unbalanced','unbalanced', unbalanced_train)
save_batches('./Embeddings/Training/Replace','replace', replace_train)

#Save Validation Embeddings
save_batches('./Embeddings/Validation/Balanced','balanced', balanced_val)
save_batches('./Embeddings/Validation/Unbalanced','unbalanced', unbalanced_val)
save_batches('./Embeddings/Validation/Replace','replace', replace_val)

# Save Test Embeddings
save_batches('./Embeddings/Testing/','geoguessr', balanced_test)
save_embeddings('./Embeddings/Testing/','tourist', tourist_test)
save_embeddings('./Embeddings/Testing/','aerial', aerial_test)