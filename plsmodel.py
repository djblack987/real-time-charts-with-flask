import pandas as pd
from datetime import datetime
import os
import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import cross_val_predict, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score

import pickle

class PLSModel:
    
    def __init__(self, headers):
        self.results_df = pd.read_csv(headers, header=0)
        
        
    def train_model(self, calibration_file):
        self.calibration_df = pd.read_csv(calibration_file, header=0)
        header_list = self.calibration_df.columns.tolist()
        header_list = header_list[4:]
    
        X = self.calibration_df[header_list].values
        y = self.calibration_df["THC Conc (wt-%)"].values
        
        # Define the parameter space for the search. Just the number of LV here
        parameters = {'n_components':np.arange(1,20,1)}
        # Define the grid-search estimator based on PLS regression
        self.pls = GridSearchCV(PLSRegression(), parameters, scoring = 'neg_mean_squared_error', verbose=0, cv=10, refit=True)
        # Fit the estimator to the data
        self.pls.fit(X, y)
        
        # Optional: print the best estimator
        # Apply the best estimator to calculate a cross-validation predicted variable
        self.y_cv = cross_val_predict(self.pls.best_estimator_, X, y, cv=10)
        # Optional: calculate figures of merit
        self.rmse, self.score = np.sqrt(mean_squared_error(y, self.y_cv)), r2_score(y, self.y_cv)
        
        with open("PLS_Model", 'wb') as file:
            pickle.dump(self.pls, file)
        
        print(f"Model trained! RMSE = {self.rmse * 100:.3f}%, R2 = {self.score:.3f}")
        print(f"Best number of LVs ={self.pls.best_params_['n_components']}")
    
    def read_csv(self, spectra):
        

        df = pd.read_csv(spectra, skiprows=(0, 1, 2, 3, 4))
        df2 = pd.read_csv(spectra, nrows=4, header=None)
        timestamp = pd.to_datetime(df2.iloc[2,1], format='%Y-%m-%d %H:%M:%S')
        
        data = df["Reflectance(%R)"].to_list()
        data.insert(0, None)
        data.insert(0, timestamp.time())
        data.insert(0, timestamp.date())
        
        self.results_df.loc[len(self.results_df)] = data
        
    def predict(self):
        
        for index, row in self.results_df.iterrows():
                prediction = self.pls.predict(row[3:].values.reshape(1, -1))
                
                self.results_df.loc[index, "THC"] = prediction[0]*100

        
    def save_results(self, filename):
        self.results_df.to_csv(filename)