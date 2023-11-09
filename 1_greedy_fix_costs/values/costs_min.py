import torch
import pdb
import numpy as np
import random
import copy as cp
from exp_configs_1 import *
from BO import *
from utils import *

RESULTS = []

for exp_config in benchmark:
    DATASET = Evaluation_data(
        exp_config["dataset"],
        exp_config["ntrain"],
        "random",
        init_strategy=exp_config["init_strategy"],
    )
    bounds_norm = DATASET.bounds_norm

    N_RUNS = exp_config["n_runs"]
    NITER = exp_config["n_iter"]
    BATCH_SIZE = exp_config["batch_size"]
    MAX_BATCH_COST = exp_config["max_batch_cost"]
    COST_AWARE_BO = exp_config["cost_aware"]
    COST_AWARE_RANDOM = False

    y_better_BO_ALL, y_better_RANDOM_ALL = [], []
    running_costs_BO_ALL, running_costs_RANDOM_ALL = [], []

    for run in range(N_RUNS):
        SEED = 111 + run
        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)

        (
            X_init,
            y_init,
            costs_init,
            X_candidate,
            y_candidate,
            costs_candidate,
        ) = DATASET.get_init_holdout_data(SEED)
        X, y = cp.deepcopy(X_init), cp.deepcopy(y_init)
        y_best = float(torch.max(y))
        model, scaler_y = update_model(X, y, bounds_norm)

        X_candidate_FULL, y_candidate_FULL = cp.deepcopy(X_candidate), cp.deepcopy(
            y_candidate
        )
        costs_FULL = cp.deepcopy(costs_candidate)
        X_candidate_BO = cp.deepcopy(X_candidate)
        y_candidate_BO = cp.deepcopy(y_candidate)
        y_candidate_RANDOM = cp.deepcopy(y_candidate).detach().numpy()

        running_costs_BO = [0]
        running_costs_RANDOM = [0]

        costs_BO = cp.deepcopy(costs_candidate)
        costs_RANDOM = cp.deepcopy(costs_candidate)

        y_better_BO = []
        y_better_RANDOM = []

        y_better_BO.append(y_best)
        y_better_RANDOM.append(y_best)
        y_best_BO, y_best_RANDOM = y_best, y_best

        # TODO: CREATE A functino also for the cost aware BO (to hide the uglyness)

        BO_data = create_data_dict_BO(
            model,
            y_best_BO,
            scaler_y,
            X,
            y,
            X_candidate_BO,
            y_candidate_BO,
            y_better_BO,
            costs_BO,
            running_costs_BO,
            bounds_norm,
            BATCH_SIZE,
            MAX_BATCH_COST,
        )

        RANDOM_data = create_data_dict_RS(
            y_candidate_RANDOM,
            y_best_RANDOM,
            costs_RANDOM,
            BATCH_SIZE,
            MAX_BATCH_COST,
            y_better_RANDOM,
            running_costs_RANDOM,
        )

        for i in range(NITER):
            if COST_AWARE_BO == False:
                BO_data = BO_CASE_1_STEP(BO_data)
            else:
                BO_data = BO_AWARE_CASE_1_STEP(BO_data)

            if COST_AWARE_RANDOM == False:
                indices_random = np.random.choice(
                    np.arange(len(y_candidate_RANDOM)), size=BATCH_SIZE, replace=False
                )
                if max(y_candidate_RANDOM[indices_random])[0] > y_best_RANDOM:
                    y_best_RANDOM = max(y_candidate_RANDOM[indices_random])[0]

                y_better_RANDOM.append(y_best_RANDOM)
                BATCH_COST = sum(costs_RANDOM[indices_random])[0]
                running_costs_RANDOM.append(running_costs_RANDOM[-1] + BATCH_COST)
                y_candidate_RANDOM = np.delete(
                    y_candidate_RANDOM, indices_random, axis=0
                )
                costs_RANDOM = np.delete(costs_RANDOM, indices_random, axis=0)
            else:
                all_cheapest_indices = np.argwhere(
                    costs_RANDOM.flatten() == 0
                ).flatten()
                indices_random = np.random.choice(
                    all_cheapest_indices, size=BATCH_SIZE, replace=False
                )
                if max(y_candidate_RANDOM[indices_random])[0] > y_best_RANDOM:
                    y_best_RANDOM = max(y_candidate_RANDOM[indices_random])[0]

                y_better_RANDOM.append(y_best_RANDOM)
                BATCH_COST = sum(costs_RANDOM[indices_random])[0]
                running_costs_RANDOM.append(running_costs_RANDOM[-1] + BATCH_COST)
                y_candidate_RANDOM = np.delete(
                    y_candidate_RANDOM, indices_random, axis=0
                )
                costs_RANDOM = np.delete(costs_RANDOM, indices_random, axis=0)

            print("--------------------")
            print(
                "# |{}/{}|\tBO {:.2f}\tRS {:.2f}\tSUM(COSTS BO): ${}\tSUM(COSTS RS): ${}\tN_train {}".format(
                    i + 1,
                    NITER,
                    BO_data["y_best_BO"],
                    y_best_RANDOM,
                    BO_data["running_costs_BO"][-1],
                    running_costs_RANDOM[-1],
                    BO_data["N_train"],
                )
            )

        y_better_BO_ALL.append(y_better_BO)
        y_better_RANDOM_ALL.append(y_better_RANDOM)
        running_costs_BO_ALL.append(running_costs_BO)
        running_costs_RANDOM_ALL.append(running_costs_RANDOM)

    y_better_BO_ALL = np.array(y_better_BO_ALL)
    y_better_RANDOM_ALL = np.array(y_better_RANDOM_ALL)

    max_n = reaching_max_n(y_better_BO_ALL)
    plot_utility_BO_vs_RS(
        y_better_BO_ALL,
        y_better_RANDOM_ALL,
        name="./figures/utility_{}_{}.png".format(
            exp_config["dataset"], exp_config["max_batch_cost"]
        ),
    )
    plot_costs_BO_vs_RS(
        running_costs_BO_ALL,
        running_costs_RANDOM_ALL,
        name="./figures/optimization_{}_{}.png".format(
            exp_config["dataset"], exp_config["max_batch_cost"]
        ),
    )

    RESULTS.append(
        {
            "settings": exp_config,
            "max_n": max_n,
            "y_better_BO_ALL": y_better_BO_ALL,
            "y_better_RANDOM_ALL": y_better_RANDOM_ALL,
            "running_costs_BO_ALL": running_costs_BO_ALL,
            "running_costs_RANDOM_ALL": running_costs_RANDOM_ALL,
        }
    )

    print("Done with experiment: ", exp_config)

print("Done with all experiments")
print("Saving results")
save_pkl(
    RESULTS,
    "results.pkl",
)
