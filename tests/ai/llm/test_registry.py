import unittest

from ai.llm import MEDGEMMA_MODEL_DEFINITIONS, MODEL_REGISTRY, ModelRegistry


class MedGemmaRegistryTest(unittest.TestCase):
    def test_compatibility_projection_uses_canonical_definitions(self) -> None:
        definitions = ModelRegistry(MEDGEMMA_MODEL_DEFINITIONS).list()

        self.assertEqual(
            [definition.id for definition in definitions],
            ["medgemma-screening", "medgemma-main"],
        )
        self.assertEqual(
            [entry.model_id for entry in MODEL_REGISTRY],
            [definition.id for definition in definitions],
        )
        self.assertEqual(
            [entry.adapter_repo for entry in MODEL_REGISTRY],
            [definition.provider_model for definition in definitions],
        )
        self.assertTrue(all(definition.provider_key == "medgemma" for definition in definitions))


if __name__ == "__main__":
    unittest.main()
