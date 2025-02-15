import numpy as np
import scipy.io as sio
import torch

from sklearn import preprocessing

"""
THIS file WAS ORIGINALLY written by:

Ksenia Konyushkova, Raphael Sznitman, Pascal Fua 'Learning Active Learning from Data', NIPS 2017

We made some modifications in order to accommodate Pytorch experiments, and provide reproducibility across multiple
experiments using seeding.
"""


class Dataset:
    """
    Written by:
        Ksenia Konyushkova, Raphael Sznitman, Pascal Fua 'Learning Active Learning from Data', NIPS 2017
    """
    def __init__(self, seed=None):
        """
        Initialize a dataset for active learning

        If 'seed' is provided, it will be used to seed an np.random.RandomState() object that will be used on each
        call to setStartState() to randomly choose which points to include in the dataset. This is used to ensure that
        the sequence of datasets used for experiments can be reproduced across multiple runs.
        """
        # each dataset will have training and test data with labels
        self.trainData = np.array([[]])
        self.trainLabels = np.array([[]])
        self.testData = np.array([[]])
        self.testLabels = np.array([[]])
        self.start_state_random = np.random.RandomState(seed) if seed is not None else np.random
        self.torch_generator = torch.Generator()
        if seed:
            self.torch_generator.manual_seed(seed)
        self.is_binary = True
        
    def setStartState(self, nStart):
        """ This functions initialises fields indicesKnown and indicesUnknown which contain the indices of labelled and unlabeled datapoints
        Input:
        nStart -- number of labelled datapoints (size of indicesKnown)
        """
        self.nStart = nStart
        # Get a point from each class
        classes = np.unique(self.trainLabels)
        self.indicesKnown = np.array([]).astype(int)
        indicesRestAll = np.array([]).astype(int)
        for cls in classes:
            cls_indices = np.nonzero(self.trainLabels==cls)[0]
            cls_indices = self.start_state_random.permutation(cls_indices)
            self.indicesKnown = np.concatenate((self.indicesKnown, np.array([cls_indices[0]])))
            indicesRestAll = np.concatenate((indicesRestAll, cls_indices[1:]))
        # permute them
        indicesRestAll = self.start_state_random.permutation(indicesRestAll)
        # if we need more than 2 datapoints, select the rest nStart-2 at random
        if nStart>len(classes):
            self.indicesKnown = np.concatenate(([self.indicesKnown, indicesRestAll[0:nStart-len(classes)]]))
        # the rest of the points will be unlabeled at the beginning
        self.indicesUnknown = indicesRestAll[nStart-2:]

    def set_start_state_torch(self, nStart):
        self.nStart = nStart
        # Get a point from each class
        classes = torch.unique(self.trainLabels)
        self.indicesKnown = torch.LongTensor()
        indicesRestAll = torch.LongTensor()
        for cls in classes:
            # Get the indices of the examples in <cls>
            cls_indices = torch.nonzero(self.trainLabels == cls, as_tuple=True)[0]
            shuffle_indices = torch.randperm(cls_indices.shape[0], generator=self.torch_generator)
            cls_indices = cls_indices[shuffle_indices]
            self.indicesKnown = torch.cat((self.indicesKnown, torch.LongTensor([cls_indices[0]])), dim=0)
            indicesRestAll = torch.cat((indicesRestAll, cls_indices[1:]), dim=0)
        # permute them
        shuffle_indices = torch.randperm(indicesRestAll.shape[0], generator=self.torch_generator)
        indicesRestAll = indicesRestAll[shuffle_indices]
        # if we need more than 2 datapoints, select the rest nStart-2 at random
        if nStart>len(classes):
            self.indicesKnown = torch.cat((self.indicesKnown, indicesRestAll[0:nStart-len(classes)]), dim=0)
        # the rest of the points will be unlabeled at the beginning
        self.indicesUnknown = indicesRestAll[nStart-2:]

    def set_is_binary(self):
        """
        Call this after the object has been filled with data
        """
        classes = np.unique(self.trainLabels)
        self.is_binary = len(classes) == 2


class DatasetCheckerboard2x2(Dataset):
    """
    Loads XOR-like dataset of checkerboard shape of size 2x2.
    Created by:
        Ksenia Konyushkova, Raphael Sznitman, Pascal Fua 'Learning Active Learning from Data', NIPS 2017
    """
    
    def __init__(self, seed=None):
        
        Dataset.__init__(self, seed)
                
        filename = './data/checkerboard2x2_train.npz'
        dt = np.load(filename)
        self.trainData = dt['x']
        self.trainLabels = dt['y']
        self.is_binary = True
                
        scaler = preprocessing.StandardScaler().fit(self.trainData)
        self.trainData = scaler.transform(self.trainData)
        
        filename = './data/checkerboard2x2_test.npz'
        dt = np.load(filename)
        self.testData = dt['x']
        self.testLabels = dt['y']
        self.testData = scaler.transform(self.testData)
        self.name = 'DatasetCheckerboard2x2'


class DatasetMNIST(Dataset):
    def __init__(self, seed=None):
        Dataset.__init__(self, seed)

        filename = './data/mnist-784_train.npz'
        dt = np.load(filename)
        self.trainData = dt['x']
        self.trainLabels = dt['y'][:,None]

        filename = './data/mnist-784_test.npz'
        dt = np.load(filename)
        self.testData = dt['x']
        self.testLabels = dt['y'][:,None]

        
class DatasetCheckerboard4x4(Dataset):
    """
    Loads XOR-like dataset of checkerboard shape of size 4x4.

    Created by:
        Ksenia Konyushkova, Raphael Sznitman, Pascal Fua 'Learning Active Learning from Data', NIPS 2017
    """
    
    def __init__(self, seed=None):
        
        Dataset.__init__(self, seed)
          
        filename = './data/checkerboard4x4_train.npz'
        dt = np.load(filename)
        self.trainData = dt['x']
        self.trainLabels = dt['y']
                
        scaler = preprocessing.StandardScaler().fit(self.trainData)
        self.trainData = scaler.transform(self.trainData)
        
        filename = './data/checkerboard4x4_test.npz'
        dt = np.load(filename)
        self.testData = dt['x']
        self.testLabels = dt['y']
        self.testData = scaler.transform(self.testData)
        self.name = 'DatasetCheckerboard4x4'
        
        
class DatasetRotatedCheckerboard2x2(Dataset):
    """
    Loads XOR-like dataset of checkerboard shape of size 2x2 that is rotated by 45'.

    Created by:
        Ksenia Konyushkova, Raphael Sznitman, Pascal Fua 'Learning Active Learning from Data', NIPS 2017
    """

    def __init__(self, seed=None):
        
        Dataset.__init__(self, seed)
                
        filename = './data/rotated_checkerboard2x2_train.npz'
        dt = np.load(filename)
        self.trainData = dt['x']
        self.trainLabels = dt['y']
        self.name = 'DatasetRotatedCheckerboard2x2'
                
        scaler = preprocessing.StandardScaler().fit(self.trainData)
        self.trainData = scaler.transform(self.trainData)
        
        filename = './data/rotated_checkerboard2x2_test.npz'
        dt = np.load(filename)
        self.testData = dt['x']
        self.testLabels = dt['y']
        self.testData = scaler.transform(self.testData)   
        
        
class DatasetSimulatedUnbalanced(Dataset):
    """
    Simple dataset with 2 Gaussian clouds is generated by this class.

    Written by:
        Ksenia Konyushkova, Raphael Sznitman, Pascal Fua 'Learning Active Learning from Data', NIPS 2017
    """
    
    def __init__(self, sizeTrain, n_dim, data_seed=12, seed=None):
        
        Dataset.__init__(self, seed)
        random = np.random.RandomState(data_seed)
        cl1_prop = random.rand()
        # we want the proportion of class 1 to vary from 10% to 90%
        cl1_prop = (cl1_prop-0.5)*0.8+0.5
        trainSize1 = int(sizeTrain*cl1_prop)
        trainSize2 = sizeTrain-trainSize1
        # the test dataset will be 10 times bigger than the train dataset.
        testSize1 = trainSize1*10
        testSize2 = trainSize2*10
        
        # generate parameters (mean and covariance) of each cloud
        mean1 = random.rand(n_dim)
        cov1 = random.rand(n_dim,n_dim)-0.5
        cov1 = np.dot(cov1,cov1.transpose())
        mean2 = random.rand(n_dim)
        cov2 = random.rand(n_dim,n_dim)-0.5
        cov2 = np.dot(cov2,cov2.transpose())
   
        # generate train data
        trainX1 = np.random.multivariate_normal(mean1, cov1, trainSize1)
        trainY1 = np.ones((trainSize1,1))
        trainX2 = np.random.multivariate_normal(mean2, cov2, trainSize2)
        trainY2 = np.zeros((trainSize2,1))
        # the test data
        testX1 = np.random.multivariate_normal(mean1, cov1, testSize1)
        testY1 = np.ones((testSize1,1))
        testX2 = np.random.multivariate_normal(mean2, cov2, testSize2)
        testY2 = np.zeros((testSize2,1))
        
        # put the data from both clouds togetehr
        self.trainData = np.concatenate((trainX1, trainX2), axis=0)
        self.trainLabels = np.concatenate((trainY1, trainY2))
        self.testData = np.concatenate((testX1, testX2), axis=0)
        self.testLabels = np.concatenate((testY1, testY2))        
        self.name = DatasetSimulatedUnbalanced
        
        
class DatasetStriatumMini(Dataset):

    """
    Dataset from CVLab. https://cvlab.epfl.ch/data/em

    Features as in:
        A. Lucchi, Y. Li, K. Smith, and P. Fua. Structured Image Segmentation Using Kernelized Features. ECCV, 2012
    """

    def __init__(self, seed=None):
        
        Dataset.__init__(self, seed)

        filename = './data/striatum_train_features_mini.mat'
        dt = sio.loadmat(filename)
        self.trainData = dt['features']
        filename = './data/striatum_train_labels_mini.mat'
        dt = sio.loadmat(filename)
        self.trainLabels = dt['labels']
        self.trainLabels[self.trainLabels==-1] = 0
        
        scaler = preprocessing.StandardScaler().fit(self.trainData)
        self.trainData = scaler.transform(self.trainData)
        
        filename = './data/striatum_test_features_mini.mat'
        dt = sio.loadmat(filename)
        self.testData = dt['features']
        filename = './data/striatum_test_labels_mini.mat'
        dt = sio.loadmat(filename)
        self.testLabels = dt['labels']
        self.testLabels[self.testLabels==-1] = 0
        self.testData = scaler.transform(self.testData)
        