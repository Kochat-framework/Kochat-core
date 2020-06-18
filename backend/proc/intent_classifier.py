"""
@author : Hyunwoong
@when : 5/9/2020
@homepage : https://github.com/gusdnd852
"""

import torch
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau

from backend.decorators import intent
from backend.loss.softmax_loss import SoftmaxLoss
from backend.proc.base.torch_processor import TorchProcessor
from util.oop import override


@intent
class IntentClassifier(TorchProcessor):

    def __init__(self, model):
        super().__init__(model=model)
        self.label_dict = model.label_dict
        self.loss = SoftmaxLoss(model.labed_dict)
        self.optimizers = [Adam(
            params=self.model.parameters(),
            lr=self.model_lr,
            weight_decay=self.weight_decay)]

        self.lr_scheduler = ReduceLROnPlateau(
            optimizer=self.optimizers[0],
            verbose=True,
            factor=self.lr_scheduler_factor,
            min_lr=self.lr_scheduler_min_lr,
            patience=self.lr_scheduler_patience)

    @override(TorchProcessor)
    def _train(self, epoch) -> tuple:
        losses, accuracies = [], []
        for train_feature, train_label in self.train_data:
            self.optimizer.zero_grad()
            x = train_feature.float().to(self.device)
            y = train_label.long().to(self.device)
            feats = self.model(x).float()
            logits = self.model.clf_logits(feats)

            total_loss = self.loss.compute_loss(logits, feats, y)
            self.loss.step(total_loss, self.optimizers)

            losses.append(total_loss.item())
            _, predict = torch.max(logits, dim=1)
            acc = self._get_accuracy(y, predict)
            accuracies.append(acc)

        loss = sum(losses) / len(losses)
        accuracy = sum(accuracies) / len(accuracies)

        if epoch > self.lr_scheduler_warm_up:
            self.lr_scheduler.step(loss)

        return loss, accuracy

    @override(TorchProcessor)
    def test(self) -> dict:
        self._load_model()
        self.model.eval()

        test_feature, test_label = self.test_data
        x = test_feature.float().to(self.device)
        y = test_label.long().to(self.device)
        feats = self.model(x).to(self.device)
        logits = self.model.clf_logits(feats)

        _, predict = torch.max(logits, dim=1)
        test_result = {'test_accuracy': self._get_accuracy(y, predict)}
        print(test_result)
        return test_result

    @override(TorchProcessor)
    def inference(self, sequence):
        self._load_model()
        self.model.eval()

        logits = self.model(sequence).float()
        logits = self.model.clf_logits(logits.squeeze())
        _, predict = torch.max(logits, dim=0)
        return list(self.label_dict)[predict.item()]