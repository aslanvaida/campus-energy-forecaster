import pandas as pd

from campus_energy_forecaster.modeling import predict, train


def test_train_then_predict_roundtrip(tmp_path, frame):
    tr, te = tmp_path / "train.csv", tmp_path / "test.csv"
    model, out = tmp_path / "models" / "model.pkl", tmp_path / "out" / "predictions.csv"
    frame.to_csv(tr, index=False)
    frame.drop(columns="energy_usage").to_csv(te, index=False)

    train.main(train_path=tr, model_path=model, n_bags=1)
    assert model.exists()

    predict.main(input_path=te, model_path=model, output_path=out)
    preds = pd.read_csv(out)
    assert list(preds.columns) == ["id", "prediction"]
    assert (preds["id"] == frame["id"]).all()
    assert preds["prediction"].notna().all()
