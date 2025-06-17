import unittest
from unittest.mock import MagicMock, patch

import torch

from sameli.models.pytorch import PyTorchModel


class PyTorchModelTestCase(unittest.TestCase):
    def setUp(self):
        self.model_name = "test_model"
        self.mock_model_path = "/tmp/fake_model.pt"
        self.artefacts = {"model": self.mock_model_path}
        self.hparams = {"feature_names": ["f1", "f2"], "device": "cpu"}

        self.model = PyTorchModel(self.model_name, self.artefacts, self.hparams)

    def test_name_property(self):
        self.assertEqual(self.model.name, self.model_name)

    def test_feature_names_property(self):
        self.assertEqual(self.model.feature_names, ["f1", "f2"])

    @patch("sameli.models.pytorch.torch.jit.load")
    def test_load_model(self, mock_jit_load):
        mock_loaded_model = MagicMock(spec=torch.jit.ScriptModule)
        mock_loaded_model.eval.return_value = mock_loaded_model

        mock_jit_load.return_value = mock_loaded_model

        loaded_model = self.model.load()

        mock_jit_load.assert_called_once_with(self.mock_model_path, map_location="cpu")
        mock_loaded_model.eval.assert_called_once()
        self.assertEqual(loaded_model, mock_loaded_model)

    def test_save_model(self):
        mock_torch_model = MagicMock(spec=torch.ScriptModule)
        self.model.save(mock_torch_model)
        self.assertEqual(self.model.model, mock_torch_model)

    def test_preprocess(self):
        input_features = {"f1": 1.5, "f2": 2.5}
        tensor = self.model.preprocess(input_features)

        expected_tensor = torch.Tensor([1.5, 2.5])
        self.assertTrue(torch.equal(tensor, expected_tensor))

    def test_predict(self):
        mock_torch_model = MagicMock(spec=torch.ScriptModule)
        mock_output = torch.Tensor([0.75])
        mock_torch_model.return_value = mock_output
        self.model.model = mock_torch_model

        input_tensor = torch.Tensor([1.5, 2.5])
        with patch("sameli.models.pytorch.torch.no_grad"):
            output = self.model.predict(input_tensor)

        mock_torch_model.assert_called_once_with(input_tensor)
        self.assertTrue(torch.equal(output, mock_output))

    def test_postprocess(self):
        prediction_tensor = torch.tensor([0.85])
        result = self.model.postprocess(prediction_tensor)
        self.assertAlmostEqual(result, 0.85)


if __name__ == "__main__":
    unittest.main()
