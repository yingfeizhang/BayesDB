#
#   Copyright (c) 2010-2013, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
import crosscat.utils.data_utils as du
import datetime
import json
import pickle
import shutil

from bayesdb.persistence_layer import PersistenceLayer
import bayesdb.settings as S


class FilePersistenceLayer(PersistenceLayer):
    """
    Stores btables in the following format in the "data" directory:
    bayesdb/data/
      <tablename>/
        data.csv
        metadata.pkl
        models.pkl

    metadata.pkl: dict. keys: M_r, M_c, T, cctypes
    models.pkl: dict[model_idx] -> (X_L, X_D). Idx starting at 1.
    data.csv: the raw csv file that the data was loaded from.
    """
    
    def __init__(self):
        ## Create data directory if doesn't exist
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.cur_dir, 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.btable_names = set()

    def get_metadata(self, tablename):
        return pickle.load(open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'r'))

    def get_models(self, tablename):
        return pickle.load(open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'r'))

    def get_csv(self, tablename):
        return open(os.path.join(self.data_dir, tablename, 'data.csv'), 'r').read()

    def start_from_scratch(self):
        """Delete all tables and all data."""
        ## TODO: prompt user to confirm
        shutil.rmtree(self.data_dir)
        os.makedirs(self.data_dir)

    def drop_btable(self, tablename):
        """Delete a single btable."""
        if tablename in self.btable_names:
            shutil.rmtree(os.path.join(self.data_dir, tablename))
            self.btable_names.remove(tablename)
        return 0

    def list_btables(self):
        """Return a list of all btable names."""
        return self.btable_names

    def delete_model(self, tablename, model_index):
        """Delete a single model"""
        models = pickle.load(open(os.path.jsoin(self.data_dir, tablename, 'models.pkl'), 'r'))
        del models[model_index]
        return 0
            
    def get_latent_states(self, tablename):
        """Return X_L_list, X_D_list, and M_c"""
        metadata = self.get_metadata(tablename)
        models = self.get_models(tablename)
        M_c = metadata['M_c']
        X_L_list = [model['X_L'] for model in models.values()]
        X_D_list = [model['X_D'] for model in models.values()]
        return (X_L_list, X_D_list, M_c)
        
    def get_metadata_and_table(self, tablename):
        """Return M_c and M_r and T"""
        metadata = self.get_metadata(tablename)
        M_c = metadata['M_c']
        M_r = metadata['M_r']
        T = metadata['T']
        return M_c, M_r, T

    def get_max_model_id(self, tablename, models=None):
        """Get the highest model id, and 0 if there are no models.
        Model indexing starts at 1 when models exist."""
        if models is None:
            models = self.get_models(tablename)
        iter_list = [model['iterations'] for model in models.values()]
        if len(iter_list) == 0:
            return 0
        else:
            return max(iter_list)

    def get_cctypes(self, tablename):
        """Access the table's current cctypes."""
        metadata = self.get_metadata(tablename)
        return metadata['cctypes']

    def update_cctypes(self, tablename, cctypes):
        """Overwrite cctypes (part of the metadata)."""
        f = open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'rw')
        metadata = pickle.load(f)
        metadata['cctypes'] = cctypes
        pickle.dump(metadata, f, pickle.HIGHEST_PROTOCOL)

    def update_metadata_and_table(self, tablename, M_r=None, M_c=None, T=None):
        """Overwrite M_r, M_c, and T (not cctypes) for the table."""
        f = open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'rw')
        metadata = pickle.load(f)
        if M_r:
            metadata['M_r'] = M_r
        if M_c:
            metadata['M_c'] = M_c
        if T:
            metadata['T'] = T
        pickle.dump(metadata, f, pickle.HIGHEST_PROTOCOL)

    def check_if_table_exists(self, tablename):
        """Return true iff this tablename exists in the persistence layer."""
        return tablename in self.btable_names

    def write_csv(self, tablename, csv):
        """
        Input: csv is the raw csv data, which gets persisted as data.csv.
        Called by create_btable_from_csv as a helper function.
        """
        if not os.path.exists(os.path.join(self.data_dir, tablename)):
            os.mkdir(os.path.join(self.data_dir, tablename))        
        f = open(os.path.join(self.data_dir, tablename, 'data.csv'), 'w')
        csv_abs_path = os.path.abspath(f.name)
        f.write(csv)
        f.close()
        return csv_abs_path

    def create_btable_from_csv(self, tablename, csv_path, csv, cctypes, postgres_coltypes, colnames):
        """
        This function is called to create a btable.
        It creates the table's persistence directory, saves data.csv and metadata.pkl.
        Creates models.pkl as empty dict.
        """
        # Make directory for table
        if not os.path.exists(os.path.join(self.data_dir, tablename)):
            os.mkdir(os.path.join(self.data_dir, tablename))        

        # Write csv
        self.write_csv(tablename, csv)

        # Write metadata
        t, m_r, m_c, header = du.read_data_objects(csv_path, cctypes=cctypes)
        metadata = dict()
        metadata['M_c'] = m_c
        metadata['M_r'] = m_r
        metadata['T'] = t
        metadata_f = open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'w')
        pickle.dump(metadata, metadata_f, pickle.HIGHEST_PROTOCOL)

        # Write models
        models = dict()
        models_f = open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'w')
        pickle.dump(models, models_f, pickle.HIGHEST_PROTOCOL)

        # Add to btable name index
        self.btable_names.add(tablename)

    def add_models(self, tablename, X_L_list, X_D_list, iterations):
        """
        Add a set of models (X_Ls and X_Ds) to a table (the table does not need to
        already have models).
        
        It is required that they all have the same number of iterations. If they have
        different numbers of iterations, call add_models multiple times.
        """
        assert len(X_L_list) == len(X_D_list)
        if os.path.exists(os.path.join(self.data_dir, tablename, 'models.pkl')):
            f = open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'r+w')                        
            models = pickle.load(f)
        else:
            f = open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'w')                        
            models = {}
        max_model_id = self.get_max_model_id(tablename, models)

        ## Model indexing starts at 1 when models exist.
        for i in range(len(X_L_list)):
            models[max_model_id + 1 + i] = dict(X_L=X_L_list[i], X_D=X_D_list[i], iterations=iterations)
        pickle.dump(models, f, pickle.HIGHEST_PROTOCOL)

    def update_model(self, tablename, X_L, X_D, iterations, modelid):
        """ Overwrite a certain model by id. """
        f = open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'r+w')
        models = pickle.load(f)
        models[modelid] = dict(X_L=X_L, X_D=X_D, iterations=iterations)
        pickle.dump(models, f, pickle.HIGHEST_PROTOCOL)

    def create_models(self, tablename, states_by_model):
        """
        Input: states_by_model is a list of (X_L, X_D).
        It is assumed that iterations=0, since this function should be called for new models only.
        Assumes that there are no models currently.
        """
        f = open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'r+w')
        models = pickle.load(f)
        for model_index, (x_l_prime, x_d_prime) in enumerate(states_by_model):
            models[model_index] = dict(X_L=X_L, X_D=X_D, iterations=0)
        pickle.dump(models, f, pickle.HIGHEST_PROTOCOL)            

    def get_model(self, tablename, modelid):
        """ Retrieve an individual (X_L, X_D, iteration) tuple, by modelid. """
        models = self.get_models(tablename)
        m = models[modelid]
        return m['X_L'], m['X_D'], m['iterations']

    def get_model_ids(self, tablename):
        """ Receive a list of all model ids for the table. """
        models = self.get_models(tablename)
        return models.keys()
            