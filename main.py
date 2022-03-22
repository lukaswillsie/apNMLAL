import getopt
import sys

import numpy as np
from sklearn.ensemble import RandomForestRegressor
# for plotting
import matplotlib.pyplot as plt

# import various AL strategies
from Classes.active_learner import ActiveLearnerRandom, ActiveLearnerPNML
from Classes.active_learner import ActiveLearnerUncertainty
from Classes.active_learner import ActiveLearnerLAL
# import the dataset class
from Classes.dataset import DatasetCheckerboard2x2, DatasetCheckerboard4x4, DatasetRotatedCheckerboard2x2, \
    DatasetStriatumMini
# import Experiment and Result classes that will be responsible for running AL and saving the results
from Classes.experiment import Experiment
from Classes.results import Results
from os.path import exists
from joblib import dump, load

lal_model_regression_path = "./pickled/lal_model_regression"
lal_model_iterative_path = "./pickled/lal_model_iterative"
temporary_results_name = "temp-results"


def build_lal_model(filename, params, pickle_path=None):
    if pickle_path and exists(pickle_path):
        return load(pickle_path)

    data_path = './lal datasets/' + filename
    regression_data = np.load(data_path)
    regression_features = regression_data['arr_0']
    regression_labels = regression_data['arr_1']

    print('Building lal regression model..')
    lalModel = RandomForestRegressor(n_estimators=params['est'], max_depth=params['depth'],
                                     max_features=params['feat'], oob_score=True, n_jobs=4)

    lalModel.fit(regression_features, np.ravel(regression_labels))

    print('Done!')
    print('Oob score = ', lalModel.oob_score_)

    if pickle_path:
        print("Pickling lal regression model..")
        dump(lalModel, pickle_path, compress=3)
        print("Done!")

    return lalModel


def build_lal_model_rand():
    """
    LAL Regression Model

    NOTE: This code was copied from the authors' original 'AL experiments.ipynb'
    """
    return build_lal_model(
        'LAL-randomtree-simulatedunbalanced-big.npz',
        {'est': 2000, 'depth': 40, 'feat': 6}
    )


def build_lal_model_iterative():
    """
    LAL Iterative Model

    NOTE: This code was copied from the authors' original 'AL experiments.ipynb'
    """
    return build_lal_model(
        'LAL-iterativetree-simulatedunbalanced-big.npz',
        {'est': 1000, 'depth': 40, 'feat': 6}
    )


def run_experiments(
    # The Dataset to use
    data,
    # List of active learners to run the experiments on
    active_learners,
    # number of experiment repeats
    num_experiments,
    # number of estimators (random trees) in the classifier
    estimators,
    # number of iterations in AL experiment
    num_iterations,
    # The name of the experiment. Will be the name of the file in ./exp
    # in which the final results will be saved
    name,
    # the quality metrics computed on the test set to evaluate active learners; default
    # is accuracy
    quality_metrics=None
):
    if quality_metrics is None:
        quality_metrics = ["accuracy"]
    exp = Experiment(num_iterations, estimators, quality_metrics, data, active_learners)
    # the Results class helps to add, save and plot results of the experiments
    res = Results(exp, num_experiments)

    for i in range(num_experiments):
        print('\n experiment #' + str(i + 1))
        # run an experiment
        performance = exp.run()
        res.addPerformance(performance)
        # Save temporary results after every experiment
        res.saveResults(temporary_results_name)
        # reset the experiment (including sampling a new starting state for the dataset)
        exp.reset()

    print()
    res.saveResults(name)


def plot_results(results_filename, out_name):
    """
    Plot the given results that were saved to disk. Results.saveResults(<results_filename>) must have been previously
    called for this to work. The plot will be saved to ./out/<out_name>.png
    """
    res2plot = Results()
    res2plot.readResult(results_filename)
    res2plot.plotResults(metrics=['accuracy'])
    plt.savefig(f"./out/{out_name}.png")


if __name__ == "__main__":
    options, arguments = getopt.getopt(
        sys.argv[1:],
        "",
        [
            "experiments=",
            "iterations=",
            "learners=",
            "dataset=",
            "name="
        ]
    )
    valid_datasets = {
        "checkerboard2x2": DatasetCheckerboard2x2,
        "checkerboard4x4": DatasetCheckerboard4x4,
        "rotatedcheckerboard2x2": DatasetRotatedCheckerboard2x2,
        "striatummini": DatasetStriatumMini
    }

    supported_learners = [
        "rand",
        "uncertainty",
        "pnml",
        "lal-rand",
        "lal-iter"
    ]

    normal_learners = {
        "rand": ActiveLearnerRandom,
        "uncertainty": ActiveLearnerUncertainty,
        "pnml": ActiveLearnerPNML
    }

    experiments = 1
    iterations = 100
    dataset = None
    name = None
    for o, a in options:
        if o == "--experiments":
            experiments = int(a)
        if o == "--iterations":
            iterations = int(a)
        if o == "--dataset":
            dataset = valid_datasets[a.lower()]()
            dataset.setStartState(2)
        if o == "--name":
            name = a

    learners = []
    # The definition of the learners relies on the other args
    for o, a in options:
        if o == "--learners":
            learners = a.split(",")
            for i, learner in enumerate(learners):
                if learner not in supported_learners:
                    print(f"Supported learners are: {supported_learners}")
                    exit(1)

                if learner in normal_learners:
                    learners[i] = normal_learners[learner](dataset, 50, learner)
                elif learner == "lal-rand":
                    model = build_lal_model_rand()
                    learners[i] = ActiveLearnerLAL(dataset, 50, learner, model)
                elif learner == "lal-iter":
                    model = build_lal_model_iterative()
                    learners[i] = ActiveLearnerLAL(dataset, 50, learner, model)

    run_experiments(
        dataset,
        learners,
        experiments,
        50,
        iterations,
        name
    )

    plot_results(name, name)
