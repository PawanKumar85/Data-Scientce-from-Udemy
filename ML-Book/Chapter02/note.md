# End-to-End Machine Learning Project

This chapter illustrates the main steps of a Machine Learning (ML) project using a fictitious real estate company scenario. The goal is to build a model to predict median housing prices in California districts using census data.

## 1. Project Steps Overview
The main steps of an ML project typically include:
*   **Look at the big picture**.
*   **Get the data**.
*   **Discover and visualize the data to gain insights**.
*   **Prepare the data for Machine Learning algorithms**.
*   **Select a model and train it**.
*   **Fine-tune your model**.
*   **Present your solution**.
*   **Launch, monitor, and maintain your system**.

## 2. Working with Real Data
It is highly recommended to experiment with **real-world data**.
*   **Sources for open datasets**: UC Irvine Machine Learning Repository, Kaggle, Amazon's AWS datasets, Data Portals, OpenDataMonitor, Quandl, Wikipedia's list of ML datasets, Quora.com, and the datasets subreddit.
*   **Dataset used**: The **California Housing Prices dataset** from the StatLib repository, based on the 1990 California census. It's suitable for learning despite being older. Each row represents a "block group" or "district" with 600-3,000 people, including metrics like population, median income, and median housing price.

## 3. Look at the Big Picture
### Frame the Problem
*   **Business Objective**: The model's output (predicted median housing price) will be fed into a downstream ML system to determine investment worthiness in an area, directly impacting revenue.
*   **Current Solution**: Housing prices are currently estimated manually by experts, which is costly, time-consuming, and often inaccurate (estimates can be off by more than 20%).
*   **ML Problem Type**:
    *   **Supervised Learning**: The dataset provides labeled training examples (each instance has the expected output: median housing price).
    *   **Regression Task**: The goal is to predict a value.
    *   **Multiple Regression**: The system uses multiple features (e.g., population, median income) for prediction.
    *   **Univariate Regression**: Only a single value (median housing price) is predicted per district.
    *   **Batch Learning**: Suitable because there's no continuous data flow, no need for rapid adjustments, and the data fits in memory. Online learning or MapReduce would be considered for huge datasets.

### Select a Performance Measure
*   **Root Mean Square Error (RMSE)**: This is a typical performance measure for regression problems. It indicates the typical error in predictions, giving **higher weight to large errors**.
    *   Formula: $RMSE(\mathbf{X}, h) = \sqrt{\frac{1}{m} \sum_{i=1}^{m} (h(\mathbf{x}^{(i)}) - y^{(i)})^2}$.
    *   Key notations include $m$ (number of instances), $\mathbf{x}^{(i)}$ (feature vector), $y^{(i)}$ (label/desired output), $\mathbf{X}$ (matrix of feature values), and $h$ (system's prediction function/hypothesis).
    *   RMSE corresponds to the **Euclidean norm ($\ell_2$ norm)**.
*   **Mean Absolute Error (MAE)**: Also known as average absolute deviation, MAE might be preferred if there are many outlier districts, as it is **less sensitive to outliers** than RMSE.
    *   Formula: $MAE(\mathbf{X}, h) = \frac{1}{m} \sum_{i=1}^{m} |h(\mathbf{x}^{(i)}) - y^{(i)}|$.
    *   MAE corresponds to the **$\ell_1$ norm (Manhattan norm)**.
*   The higher the norm index (e.g., $\ell_2$ vs $\ell_1$), the more it focuses on large values.

### Check the Assumptions
It's crucial to list and verify assumptions early to avoid serious issues. For example, ensuring the downstream system truly needs actual prices rather than categories.

## 4. Get the Data
*   **Workspace Setup**: Requires Python, Jupyter, NumPy, pandas, Matplotlib, and Scikit-Learn. **Using an isolated environment (like virtualenv) is highly recommended** to prevent library version conflicts across projects.
*   **Data Download & Load**: The dataset is a single compressed `housing.tgz` file containing `housing.csv`. It's best to automate data fetching and loading using functions (e.g., `fetch_housing_data()` and `load_housing_data()` for reproducibility).
*   **Data Structure Quick Look**:
    *   `head()`: Shows the top rows and attributes like `longitude`, `latitude`, `housing_median_age`, `total_rooms`, `total_bedrooms`, `population`, `households`, `median_income`, `median_house_value`, and `ocean_proximity`.
    *   `info()`: Reveals 20,640 instances. **`total_bedrooms` has 207 missing values**. All attributes are numerical except `ocean_proximity`, which is a categorical text attribute.
    *   `value_counts()`: Confirms `ocean_proximity` categories like `<1H OCEAN`, `INLAND`, `ISLAND`, `NEAR BAY`, `NEAR OCEAN`.
    *   `describe()`: Provides a summary of numerical attributes, including count, mean, min, max, standard deviation (`std`), and percentiles (25th, 50th/median, 75th).
    *   `hist()`: Plots histograms for each numerical attribute.
        *   **Key Observations**:
            *   `median_income` is scaled and capped (0.5 to 15).
            *   `housing_median_age` and `median_house_value` are also capped (e.g., median house value at $500,000), which **can be a serious problem for the target attribute** if precise predictions beyond this limit are needed. Solutions include collecting proper labels or removing capped districts.
            *   Attributes have very different scales, requiring feature scaling later.
            *   Many histograms are **tail-heavy**, which may hinder some ML algorithms.

### Create a Test Set
*   **Avoid Data Snooping Bias**: It is **critical to create a test set at this early stage and keep it separate**, never looking at it until the final model evaluation. This prevents **overfitting** to the test data due to pattern detection (data snooping bias).
*   **Random Sampling**: Can be done by picking instances randomly, typically 20% of the dataset. However, a simple random split can generate different test sets each run, or become inconsistent with updated datasets. Setting a random seed (e.g., `np.random.seed(42)`) can make it reproducible but not stable for updated data.
*   **Stable Train/Test Split**: Use an instance's unique and immutable identifier (e.g., a hash of the ID) to consistently assign instances to the test set.
*   **Scikit-Learn's `train_test_split()`**: Offers `random_state` for reproducibility and can split multiple datasets consistently.
*   **Stratified Sampling**: **Highly recommended for smaller datasets or when an attribute is very important** to ensure the test set is representative of the overall population, mirroring the proportions of specific categories (strata).
    *   For the housing data, `median_income` is crucial. It's divided into 5 income categories using `pd.cut()`.
    *   Scikit-Learn's **`StratifiedShuffleSplit`** is used to create training and test sets with proportional income categories, preventing sampling bias that purely random sampling might introduce.
*   After creation, the temporary `income_cat` attribute should be removed.

## 5. Discover and Visualize the Data to Gain Insights
*   Work on a copy of the training set.
*   **Geographical Visualization**: Scatterplots of `longitude` vs. `latitude` with `alpha=0.1` reveal high-density areas (Bay Area, LA, San Diego, Central Valley).
*   **Housing Prices Visualization**: A scatterplot with circle radius representing population and color representing `median_house_value` (using `jet` colormap) shows that **housing prices are strongly related to location (e.g., ocean proximity) and population density**.
*   **Looking for Correlations**:
    *   The `corr()` method computes Pearson's r (standard correlation coefficient) between attributes.
    *   Correlations with `median_house_value`: `median_income` has a strong positive correlation (0.687170), while `latitude` has a small negative correlation (-0.142826).
    *   **Correlation coefficients measure linear relationships** and range from -1 (strong negative) to 1 (strong positive), with 0 indicating no linear correlation. They can miss nonlinear relationships.
    *   `scatter_matrix()` from pandas plots every numerical attribute against every other, showing histograms on the diagonal.
    *   **`median_income` is the most promising attribute** for predicting `median_house_value`, showing a strong upward trend. Price caps (e.g., at $500,000) are clearly visible as horizontal lines, which may be data quirks to address.
*   **Experimenting with Attribute Combinations**: Creating new attributes can provide more useful insights for ML algorithms.
    *   Examples: `rooms_per_household`, `bedrooms_per_room`, `population_per_household`.
    *   `bedrooms_per_room` showed a much stronger negative correlation with median house value (-0.259984) than `total_bedrooms` or `total_rooms`, suggesting lower bedroom/room ratios indicate more expensive homes.
*   This exploration phase is iterative; insights gained from initial prototypes can lead back to further data exploration.

## 6. Prepare the Data for Machine Learning Algorithms
It's essential to **write functions for data transformations** to ensure reproducibility, reususability, enable use in live systems, and facilitate experimentation with different transformations.
*   Separate predictors (`housing`) from labels (`housing_labels`).

### Data Cleaning (Missing Values)
*   The `total_bedrooms` attribute has missing values.
*   **Three options to handle missing values**:
    1.  Remove corresponding districts (`dropna()`).
    2.  Remove the whole attribute (`drop()`).
    3.  Set values to some value (zero, mean, **median**) (`fillna()`).
*   **Scikit-Learn's `SimpleImputer`**: This class can replace missing values with the median of each attribute. It must be `fit()` on the training data only, and then used to `transform()` both the training and test sets (and new data).

### Scikit-Learn Design Principles
Scikit-Learn's API follows key design principles:
*   **Consistency**: All objects share a simple interface:
    *   **Estimators**: Objects that estimate parameters (`fit()` method).
    *   **Transformers**: Estimators that can transform datasets (`transform()`, `fit_transform()`).
    *   **Predictors**: Estimators that make predictions (`predict()`, `score()`).
*   **Inspection**: Hyperparameters are public instance variables (e.g., `imputer.strategy`), and learned parameters have an underscore suffix (e.g., `imputer.statistics_`).
*   **Nonproliferation of classes**: Datasets are represented as NumPy arrays or SciPy sparse matrices.
*   **Composition**: Building blocks are reused (e.g., `Pipeline`).
*   **Sensible defaults**: Reasonable default values are provided for most parameters.

### Handling Text and Categorical Attributes
*   The `ocean_proximity` attribute is categorical.
*   **`OrdinalEncoder`**: Converts text categories to numbers.
    *   **Issue**: This method can mislead ML algorithms by implying numerical similarity between categories that don't have an inherent order (e.g., `<1H OCEAN` and `INLAND` are not "closer" than `<1H OCEAN` and `NEAR BAY`).
*   **`OneHotEncoder`**: A common solution to the ordinal encoder issue. It creates one binary attribute per category (dummy attributes), where only one attribute is 'hot' (1) and others are 'cold' (0).
    *   Outputs a **SciPy sparse matrix** for memory efficiency, especially with many categories. It can be converted to a dense NumPy array using `toarray()`.
    *   For attributes with many categories, alternative approaches include replacing them with useful numerical features (e.g., distance to ocean) or using **embeddings** (learnable, low-dimensional vectors).

### Custom Transformers
*   Custom transformers can be created to handle unique cleanup operations or combine attributes. They should inherit `BaseEstimator` and `TransformerMixin` to work seamlessly with Scikit-Learn pipelines.
*   Example: `CombinedAttributesAdder` creates `rooms_per_household`, `bedrooms_per_room`, and `population_per_household`.
*   These custom transformers can include hyperparameters (e.g., `add_bedrooms_per_room`) to allow automated tuning of data preparation steps.

### Feature Scaling
*   **Feature scaling is critical for most ML algorithms** because they perform poorly with input numerical attributes that have vastly different scales (e.g., total rooms from 6 to 39,320 vs. median income from 0 to 15). Scaling target values is generally not required.
*   **Two common ways**:
    1.  **Min-max scaling (Normalization)**: Shifts and rescales values to range from 0 to 1 (`MinMaxScaler`).
    2.  **Standardization**: Subtracts the mean and divides by the standard deviation, resulting in zero mean and unit variance. It is **less affected by outliers** than min-max scaling. (`StandardScaler`).
*   **Important**: Scalers must be `fit()` only on the **training data**.

### Transformation Pipelines
*   **`Pipeline` (Scikit-Learn)**: Helps execute multiple data transformation steps in the correct order. It takes a list of name/estimator pairs. All but the last estimator must be transformers.
*   **`ColumnTransformer` (Scikit-Learn 0.20+)**: Enables applying different transformations to different columns within a single transformer. It can combine numerical pipelines (e.g., for imputation, attribute addition, scaling) and categorical encoders (e.g., `OneHotEncoder`).
    *   It concatenates outputs along the second axis and can return a sparse matrix if the density is low.
    *   Columns can also be "dropped" or "passthrough".

## 7. Select and Train a Model
*   **Training and Evaluation on Training Set**:
    *   **Linear Regression Model**: Initial training results in an RMSE of approximately **$68,628**, which is not satisfying and suggests **underfitting** the training data. Underfitting can be addressed by selecting a more powerful model, using better features, or reducing model constraints.
    *   **DecisionTreeRegressor**: Initial training shows an RMSE of **0.0**, indicating that the model has **badly overfit the training data**.
*   **Better Evaluation Using Cross-Validation**:
    *   **K-fold cross-validation** using Scikit-Learn's `cross_val_score` is a great alternative to a simple train/validation split. It splits the training set into `k` (e.g., 10) distinct folds, training and evaluating the model `k` times, using a different fold for evaluation each time.
    *   The `scoring` parameter is set to `neg_mean_squared_error` because Scikit-Learn expects a utility function (higher is better).
    *   **Decision Tree RMSE (cross-validated)**: Mean RMSE of approximately **$71,407** (with a standard deviation of $2,439), confirming its overfitting compared to the Linear Regression model.
    *   **Linear Regression RMSE (cross-validated)**: Mean RMSE of approximately **$69,052** (with a standard deviation of $2,731).
    *   **RandomForestRegressor**: This is an **Ensemble Learning** model that combines multiple Decision Trees. It performs much better, with a cross-validated mean RMSE of approximately **$50,182** (std: $2,097). Although better, it still shows some overfitting (training score lower than validation).
*   **Model Selection Strategy**: Shortlist a few (2-5) promising models from various categories (e.g., Support Vector Machines, Neural Networks) without over-tweaking hyperparameters yet.
*   **Saving Models**: **Save every model experiment** (hyperparameters, trained parameters, cross-validation scores, predictions) using Python's `pickle` module or the more efficient `joblib` library.

## 8. Fine-Tune Your Model
*   **Grid Search**: **`GridSearchCV`** from Scikit-Learn automates hyperparameter tuning by evaluating all possible combinations of specified hyperparameter values using cross-validation.
    *   Example: For `RandomForestRegressor`, `GridSearchCV` explores combinations of `n_estimators`, `max_features`, and `bootstrap`.
    *   `grid_search.best_params_` and `grid_search.best_estimator_` provide the best found parameters and the corresponding model.
    *   By default (`refit=True`), the best estimator is retrained on the entire training set for improved performance.
    *   Fine-tuning the `RandomForestRegressor` improved the RMSE from $50,182 to **$49,682**.
    *   It's possible to treat data preparation steps as hyperparameters within the grid search (e.g., including `add_bedrooms_per_room` in the search).
*   **Randomized Search**: **`RandomizedSearchCV`** is preferred when the hyperparameter search space is large. Instead of trying all combinations, it samples a given number of random combinations, offering more control over the computing budget and exploring more values per hyperparameter.
*   **Ensemble Methods**: Combining multiple best-performing models (Ensemble Learning) often yields better results than individual models, especially if they make different types of errors.
*   **Analyze Best Models and Their Errors**:
    *   **Feature Importances**: Models like `RandomForestRegressor` can indicate the relative importance of each attribute for predictions (e.g., `median_income` and `INLAND` were most important). This insight can guide feature selection.
    *   **Error Analysis**: Inspecting specific errors helps understand why they occur and suggests fixes (e.g., adding/removing features, cleaning outliers).

### Evaluate Your System on the Test Set
*   This **final evaluation** should only be done once the model is fine-tuned and you are confident in it.
*   The `full_pipeline.transform()` method is used on the test set (do not use `fit_transform()` on test data as it would "fit" the scaler to the test set, leading to data leakage).
*   The final RMSE on the test set was approximately **$47,730.2**.
*   A **95% confidence interval** can be computed (e.g., using `scipy.stats.t.interval()`) to understand the precision of the generalization error estimate.
*   Performance on the test set may sometimes be slightly worse than observed during cross-validation due to fine-tuning for validation data. It's crucial to **resist the temptation to tweak hyperparameters based on test set performance**, as this can lead to poor generalization to new, unseen data.

## 9. Present Your Solution
*   Clearly present what was learned, what worked, what didn't, assumptions made, and the system's limitations.
*   Provide clear visualizations and memorable statements (e.g., "median income is the number one predictor of housing prices").
*   Even if the ML system doesn't outperform human experts (e.g., if it's still off by 20%), it might still be valuable if it frees up expert time for more productive tasks.

## 10. Launch, Monitor, and Maintain Your System
### Launch/Deployment
*   **Prepare for Production**: Polish code, write documentation and tests.
*   **Deployment Methods**:
    *   **Saving and Loading**: Save the trained Scikit-Learn model (including the full preprocessing and prediction pipeline) using `joblib`, then load and use it in the production environment by calling its `predict()` method.
    *   **Web Service (REST API)**: Wrap the model within a dedicated web service. This allows for easier model upgrades without interrupting the main application, simplifies scaling, and allows the web application to use any language.
    *   **Cloud Deployment**: Deploy on platforms like Google Cloud AI Platform by saving the model (e.g., with `joblib`) and uploading it, providing a scalable web service.

### Monitoring
*   **Live Performance Check**: Crucial to implement monitoring code to check system performance regularly and trigger alerts if it drops.
*   **Model "Rot"**: Models can degrade over time due to changes in the real world (data drift), requiring retraining.
*   **Performance Metrics**:
    *   **Downstream Metrics**: Performance can sometimes be inferred from business metrics (e.g., sales for a recommender system).
    *   **Human Analysis**: For tasks where performance isn't easily quantifiable (e.g., image classification for product defects), human raters can evaluate samples of model classifications.
*   **Monitoring is often more work than building and training the model itself**.

### Maintenance (Automation)
*   **Automate as much as possible**:
    *   Regularly collect and label fresh data.
    *   Automate model training and hyperparameter tuning (e.g., daily/weekly scripts).
    *   Automate evaluation of new models against previous ones on updated test sets, deploying only if performance hasn't decreased.
*   **Monitor Input Data Quality**: Trigger alerts for issues like missing features, mean/standard deviation drift, or new categories in categorical features.
*   **Backups**: Maintain backups of every model version and dataset version for quick rollbacks, comparison, and evaluation against historical data.
*   **Test Set Subsets**: Create specialized test set subsets (e.g., most recent data, inland vs. near-ocean districts) to gain deeper understanding of model strengths and weaknesses.

## Conclusion
A significant portion of an ML project involves **data preparation, building monitoring tools, setting up human evaluation pipelines, and automating regular model training**. While ML algorithms are important, it's often more beneficial to be comfortable with the overall process and know a few algorithms well rather than focusing excessively on advanced algorithms. It is recommended to practice by selecting a dataset (e.g., from Kaggle) and working through the entire process.
