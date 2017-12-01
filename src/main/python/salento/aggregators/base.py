# Copyright 2017 Rice University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import json
import tensorflow as tf
import random

from salento.models.low_level_evidences.infer import BayesianPredictor


class Aggregator(object):
    """
    The base class for aggregators
    """

    def __init__(self, data_file, model_dir):
        """
        :param data_file: the data file, should have evidences extracted
        :param model_dir: directory where model is stored
        """
        self._data_file = data_file
        self._model_dir = model_dir
        self.END_OF_SEQUENCE_MARKER = 'STOP'

    def __enter__(self):
        print('Loading model...', end='', flush=True)
        self.sess = tf.Session()
        self.model = BayesianPredictor(self._model_dir, self.sess)
        print('done')

        print('Loading data...', end='', flush=True)
        with open(self._data_file) as f:
            self.dataset = json.load(f)
        print('done')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sess.close()

    def get_latent_specification(self, evidences):
        """
        Return the latent specification for a given set of evidences
        :param evidences: the evidences as a dictionary (internally, Salento will look for the key "apicalls")
        :return: the latent specification tensor
        """
        spec = self.model.psi_from_evidence(evidences)
        return spec

    def distribution_next_call(self, spec, sequence, call=None):
        """
        Get a distribution over the next call in a sequence
        :param spec: the latent spec, get it from get_latent_specification
        :param sequence: the sequence
        :param call: if given, return the probability of this call instead of the whole distribution
        :return: distribution over the next call, or if call is given, probability of the call
        """
        dist = self.model.infer_step(spec, sequence, step='call')
        return dist if call is None else dist[call]

    def distribution_next_state(self, spec, sequence, state=None):
        """
        Get a distribution over the next state of the last call in a sequence
        :param spec: the latent spec, get it from get_latent_specification
        :param sequence: the sequence
        :param state: (0 or 1) if given, return the probability of this state instead of the whole distribution
        :return: distribution over the next state, or if state is given, probability of the state
        :raise ValueError: if sequence was empty
        """
        if len(sequence) == 0:
            raise ValueError('Sequence cannot be empty when querying next state')
        dist = self.model.infer_step(spec, sequence, step='state')
        if state is None:
            return dist
        idx = len(sequence[-1]['states'])  # get how many states are in last call
        return dist['{}#{}'.format(idx, state)]

    def sample_from_dist(self, dist):
        """
        Random sample of k from a dictionary of (k, v) entries where v is the probability of k
        :param dist: dictionary representing a probability distribution
        :return: randomly sampled key according to the distribution
        :raise ValueError: if distribution was invalid
        """
        roll = random.random()
        total = 0
        for k, v in dist:
            total += v
            if total >= roll:
                return k
        raise ValueError('Invalid distribution: {}'.format(dist))

    def sample_next_call(self, spec, sequence):
        """
        Sample the next call in a sequence
        :param spec: the latent spec, get it from get_latent_specification
        :param sequence: the sequence
        :return: randomly sampled call from the distribution over the next call in the sequence
        :raise ValueError: if prediction from the model is not a call
        """
        dist = self.distribution_next_call(spec, sequence)
        prediction = self.sample_from_dist(dist)
        if '#' in prediction:  # state!
            raise ValueError('Improper call predicted by model: {}'.format(prediction))
        return prediction

    def sample_next_state(self, spec, sequence):
        """
        Sample the next state of the last call in a sequence
        :param spec: the latent spec, get it from get_latent_specification
        :param sequence: the sequence
        :return: randomly sampled state from the distribution over the next state of the last call in the sequence
        :raise ValueError: if prediction from the model is not a state
        """
        dist = self.distribution_next_state(spec, sequence)
        prediction = self.sample_from_dist(dist)
        if prediction != 'STOP' and '#' not in prediction:  # call!
            raise ValueError('Improper state predicted by model: {}'.format(prediction))
        return prediction

    def packages(self):
        """
        Get a list of packages in the dataset
        """
        return self.dataset['packages']

    def sequences(self, package):
        """
        Get the list of sequences in the given package
        """
        return package['data']

    def invocations(self, sequence):
        """
        Get the list of invocations in the given sequence
        """
        return sequence['sequence']

    def run(self):
        """
        Run the aggregator (should be overridden in subclasses)
        :return: anything, depending on the application of the aggregator
        """
        raise NotImplementedError('run() has not been implemented.')