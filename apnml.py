import copy
import pickle

import numpy as np
import torch
from Classes.dataset import DatasetMNIST, DatasetCheckerboard2x2
from Classes.models import SimpleMLP
from scipy import stats
from torch import optim
from torch.nn import BCEWithLogitsLoss, CrossEntropyLoss
from Classes.svi import GaussianSVI
from util import fit, evaluate, predict_probabilities


def log_prior(latent):
    normal = torch.distributions.normal.Normal(0, 1)
    return torch.sum(normal.log_prob(latent), axis=-1)

def log_likelihood(latent):
    batch_size = latent.shape[0]
    result = np.zeros(batch_size)
    known_data = dataset.trainData[dataset.indicesKnown, :]
    known_labels = dataset.trainLabels[dataset.indicesKnown, :]
    for n in range(batch_size):
        model.set_parameters(latent[n, :])
        probabilities = torch.Tensor(predict_probabilities(model, known_data))
        print(probabilities.shape)
        log_prob = torch.sum(torch.log(torch.maximum(torch.gather(probabilities, dim=1, index=torch.Tensor(known_labels).long()), torch.Tensor([1e-9]))))
        result[n] = log_prob
    return torch.Tensor(result)

def log_joint(latent):
    return log_likelihood(latent) + log_prior(latent)

def get_approximate_posterior():
    # Hyperparameters
    n_iters = 10000
    num_samples_per_iter = 500

    svi = GaussianSVI(true_posterior=log_joint, num_samples_per_iter=num_samples_per_iter)

    # Set up optimizer.
    D = model.total_params
    init_mean = torch.randn(D)
    init_mean.requires_grad = True
    init_log_std  = torch.randn(D)
    init_log_std.requires_grad = True
    init_params = (init_mean, init_log_std)

    params = init_params

    def callback(params, t):
        if t % 25 == 0:
            print("Iteration {} lower bound {}".format(t, svi.objective(params)))

    def update(params):
        optim = torch.optim.SGD(params, lr=1e-5, momentum=0.9)
        optim.zero_grad()
        loss = svi.objective(params)
        loss.backward()
        optim.step()
        return params

    # Main loop.
    print("Optimizing variational parameters...")
    for i in range(n_iters):
        params = update(params)
        callback(params, i)

    return params

@staticmethod
def criterion(m, inputs, labels, svi_mean, svi_logstd, multiclass=False):
    if multiclass:
        logits = m(inputs)
        assert logits.shape[-1] > 1
        softmax = torch.nn.Softmax(dim=1)
        probability = softmax(logits)
    else:
        logits = m(inputs)
        assert logits.shape[-1] == 1
        sigmoid = torch.nn.Sigmoid()
        pos_probability = sigmoid(logits)
        probability = torch.Tensor([1-pos_probability, pos_probability])

    return -(torch.sum(torch.log(torch.gather(probability, dim=1, index=labels.long()))) + GaussianSVI.diag_gaussian_logpdf(m.get_parameters(), svi_mean, svi_logstd))

def selectNext():
    # 1. For each unlabelled point x
    #   i. For each label t
    #       a. Add the (x, t) pair to the data and fit
    #       b. Get p(t|x) and store
    #   ii. Normalize p(t | x) for all t
    #   iii. Compute uncertainty using some metric
    #   iv. Update index of most uncertain point if necessary
    max_uncertainity = float("-inf")
    selectedIndex = -1
    selectedIndex1toN = -1

    known_data = dataset.trainData[dataset.indicesKnown, :]
    known_labels = dataset.trainLabels[dataset.indicesKnown, :]

    (svi_mean, svi_log_std) = get_approximate_posterior()
    svi_mean.requires_grad = False
    svi_log_std.requires_grad = False

    points_seen = 0
    for i, unknown_index in enumerate(dataset.indicesUnknown):
        label_probabilities = []
        for j, t in enumerate(classes):
            temp_model = copy.deepcopy(model)
            train_data = torch.cat(
                (
                    known_data,
                    dataset.trainData[(unknown_index,), :]
                ),
                dim=0
            )
            train_labels = torch.cat(
                (
                    known_labels,
                    (torch.Tensor([[t]]) if is_binary else torch.LongTensor([[t]]))
                ),
                dim=0
            )
            fit(temp_model, train_data, train_labels, criterion=lambda m, i, l: criterion(m, i, l, svi_mean, svi_log_std, True))
            # Get the probability predicted for class t
            pred = predict_probabilities(temp_model, dataset.trainData[(unknown_index,), :])[:, j]
            label_probabilities.append(pred)
        label_probabilities = np.array(label_probabilities)
        # stats.entropy() will automatically normalize
        entropy = stats.entropy(label_probabilities)
        if entropy > max_uncertainity:
            max_uncertainity = entropy
            selectedIndex = unknown_index
            selectedIndex1toN = i
        points_seen += 1
        print(points_seen)

    dataset.indicesKnown = np.concatenate(([dataset.indicesKnown, np.array([selectedIndex])]))
    dataset.indicesUnknown = np.delete(dataset.indicesUnknown, selectedIndex1toN)


experiments = 1
iterations = 100
dataset = DatasetCheckerboard2x2()
dataset.setStartState(2)

dataset.trainData = torch.from_numpy(dataset.trainData).float()
dataset.trainLabels = torch.from_numpy(dataset.trainLabels).float()
dataset.testData = torch.from_numpy(dataset.testData).float()
dataset.testLabels = torch.from_numpy(dataset.testLabels).float()

classes = torch.unique(dataset.trainLabels)
is_binary = len(classes) == 2

if not is_binary:
    dataset.trainLabels = dataset.trainLabels.long()
    classes = torch.unique(dataset.trainLabels)

# model = SimpleMLP([2,10,10,1])
model = SimpleMLP([2,10,10,1])

multiclass_loss = CrossEntropyLoss()

def multiclass_criterion(outputs, labels):
    # CrossEntropyLoss requires flattened labels
    return multiclass_loss(outputs, labels.view(-1))

loss_function = BCEWithLogitsLoss()

accuracies = []
for experiment in range(experiments):
    for iteration in range(iterations):
        # 1. Train the model
        # 2. Evaluate the model
        # 3. Select the next point
        known_data = dataset.trainData[dataset.indicesKnown, :]
        known_labels = dataset.trainLabels[dataset.indicesKnown, :]
        fit(model, 1000, 1e-2, lambda m: loss_function(m(known_data), known_labels), early_stopping_patience=40)
        accuracies.append(evaluate(model, dataset))
        print(accuracies[-1])
        pickle.dump(accuracies, open("accuracies.pkl", "wb"))
        selectNext()