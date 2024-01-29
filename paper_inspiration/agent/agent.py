import torch as T
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np

from gym_game.paper.paper_model import DeepQLearningNetwork


class MyAgent():
    # gamma -> weighting factor of the future rewards
    # epsilon -> to choice an action for exploration or exploitation
    # eps_dec -> to decrement epsilon at each step
    # eps_end -> minimum value for epsilon
    # batch_size -> batch dimension which contains the agent memory
    # input_dim is the game grid dimension
    def __init__(self, gamma, epsilon, lr, input_dim, batch_size, n_actions, max_mem_size=100000, eps_end=0.01,
                 eps_dec=5e-4):
        self.gamma = gamma
        self.epsilon = epsilon
        self.eps_min = eps_end
        self.eps_dec = eps_dec

        self.lr = lr
        self.action_space = [i for i in range(n_actions)]
        self.mem_size = max_mem_size
        self.batch_size = batch_size
        self.mem_counter = 0  # point at the first memory available

        #self.Q_eval = DeepQNetwork(lr=self.lr, input_dim=input_dim, n_actions=n_actions)
        self.Q_eval = DeepQLearningNetwork(lr=self.lr, action_space=n_actions)
        # To store the agent memory. Contains matrixs with dimension equal to input_dim, therefore the game grid
        self.state_memory = np.zeros((self.mem_size, *input_dim), dtype=np.float32)

        # To store the new state that the agent encounters
        self.new_state_memory = np.zeros((self.mem_size, *input_dim), dtype=np.float32)

        # To store the action made by the agent during the game
        self.action_memory = np.zeros(self.mem_size, dtype=np.float32)

        # To store the agent reward obtained during the game
        self.reward_memory = np.zeros(self.mem_size, dtype=np.float32)

        # ????? To manage the terminal state because the game terminate and we restart the game.
        # So the featue value of the terminal state is 0 and this help the agent to estimate the action value function.
        # Here we store the done flag
        self.terminal_memory = np.zeros(self.mem_size, dtype=bool)

    def store_transition(self, state, action, reward, new_state, done):
        # Index of the first available cell in memory
        index = self.mem_counter % self.mem_size
        self.state_memory[index] = state
        self.action_memory[index] = action
        self.reward_memory[index] = reward
        self.new_state_memory[index] = new_state
        self.terminal_memory[index] = done

        self.mem_counter += 1

    def choose_action(self, observation):  # observation is the actual state
        action = None
        # If it is grater than epsilon the agent make the best known action
        if np.random.random() > self.epsilon:
            # EXPLOITATION
            state = T.FloatTensor(observation).unsqueeze(0).to(self.Q_eval.device)  # Transform it in tensor and add a dimension (batch dimension)
            actions = self.Q_eval(state)  # Take prediction
            print("Predizione modello (singola griglia): ", actions)
            actions = F.softmax(actions,
                                dim=1)  # dim=0 because the model output has only one dimension, it is a 1d array
            print("Dopo softmax (singola griglia): ", actions)
            _, action = T.max(actions, 1)
            action = action.cpu().numpy()
        else:
            # Random action -> EXPLORATION
            action = np.random.choice(self.action_space)

        return action

    def learn(self):
        # At the beginning the memory is zeros/random, therefore until the memory is not filled (at leat the memory has the same dimension of batch) we go ahead
        if self.mem_counter < self.batch_size:
            return

        # Set the gradiet to 0
        self.Q_eval.optimizer.zero_grad()

        max_memory = min(self.mem_counter,
                         self.mem_size)  # because we want to select the last filled memory, namely a subset so we need the position of the maximum

        # Extract random states (their position) in the memory to create a batch
        batch = np.random.choice(max_memory, self.batch_size, replace=False)

        batch_index = np.arange(self.batch_size, dtype=np.int32)

        # Get the state and transform it in tensor
        state_batch = T.tensor(self.state_memory[batch]).to(self.Q_eval.device)
        new_state_batch = T.tensor(self.new_state_memory[batch]).to(self.Q_eval.device)
        reward_batch = T.tensor(self.reward_memory[batch]).to(self.Q_eval.device)
        terminal_batch = T.tensor(self.terminal_memory[batch]).to(self.Q_eval.device)

        action_batch = self.action_memory[batch]
        q_eval = self.Q_eval(state_batch)[batch_index, action_batch]  # actions performed on the "actual state"
        q_next = self.Q_eval(new_state_batch)  # actions performed on the next state
        q_next[terminal_batch] = 0.0  # ????

        # Parte tra quadre della forma del Q learning, parte iniziale!?
        q_target = reward_batch + self.gamma * T.max(q_next, dim=1)[0]

        loss = self.Q_eval.loss(q_target, q_eval).to(self.Q_eval.device)
        loss.backward()

        self.Q_eval.optimizer.step()

        self.epsilon = self.epsilon - self.eps_dec if self.epsilon > self.eps_min else self.eps_min

    def save_model(self, id, data_path):
        T.save(self.Q_eval.state_dict(), data_path +
        " /dqn_model_" + id + ".pt")

    def load_model(self, id, data_path):
        self.Q_eval.load_state_dict(T.load(data_path +
        " /dqn_model_" + id + ".pt"))











