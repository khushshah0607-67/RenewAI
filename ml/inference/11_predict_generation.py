import pandas as pd
import numpy as np
import joblib

# Set the model and feature paths
model_path = "ml/models/solar_xgb_tuned.joblib"
feature_path = "data/processed/xgboost_feature_columns.csv"

# Load the trained model
print("Loading trained XGBoost model...")

model = joblib.load(model_path)

# Load the feature names used by the model
feature_data = pd.read_csv(feature_path)

feature_columns = feature_data["feature"].tolist()

print("Model loaded successfully!")
print("Number of features:", len(feature_columns))


def predict_generation(input_data):
    # Convert input data into a DataFrame
    input_df = pd.DataFrame([input_data])

    # Check for missing features
    missing_features = [
        feature
        for feature in feature_columns
        if feature not in input_df.columns
    ]

    # Stop if required features are missing
    if missing_features:
        raise ValueError(
            "Missing features: "
            + ", ".join(missing_features)
        )

    # Arrange features in the correct model order
    input_df = input_df[feature_columns]

    # Generate prediction
    prediction = model.predict(input_df)

    # Prevent negative generation predictions
    prediction = np.maximum(
        prediction[0],
        0
    )

    # Return the prediction
    return float(prediction)


# Test the inference function
if __name__ == "__main__":

    # Create a sample input using the required model features
    sample_input = {
        "ac_power_kw": 18000,
        "irradiation": 0.75,
        "ambient_temperature": 30,
        "module_temperature": 42,
        "hour": 11,
        "day_of_week": 2,
        "day_of_year": 150,
        "month": 5,
        "hour_sin": np.sin(2 * np.pi * 11 / 24),
        "hour_cos": np.cos(2 * np.pi * 11 / 24),
        "day_of_year_sin": np.sin(2 * np.pi * 150 / 365),
        "day_of_year_cos": np.cos(2 * np.pi * 150 / 365),
        "lag_1": 17500,
        "lag_2": 17000,
        "lag_4": 16000,
        "lag_24": 12000,
        "lag_96": 10000,
        "rolling_mean_4": 17200,
        "rolling_mean_12": 16500,
        "rolling_mean_24": 15000,
        "rolling_std_24": 3000
    }

    # Generate the prediction
    prediction = predict_generation(
        sample_input
    )

    print("\nSample prediction:")
    print(
        "Predicted next 15-minute generation:",
        round(prediction, 2),
        "kW"
    )

    print("\nInference test completed successfully!")