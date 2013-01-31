#ifndef GUARD_componentmodel_h
#define GUARD_componentmodel_h

#define _USE_CMATH_DEFINES
#include <cmath>
#include <iostream>
#include <sstream>
#include <map>
#include <string>
#include <vector>
#include "utils.h"

class ComponentModel {
 public:
  //
  // getters
  std::map<std::string, double> get_hypers() const;
  int get_count() const;
  std::map<std::string, double> get_suffstats() const;
  //
  // calculators
  virtual double calc_marginal_logp() const = 0;
  virtual double calc_element_predictive_logp(double element) const = 0;
  virtual std::vector<double> calc_hyper_conditionals(std::string which_hyper,
						      std::vector<double> hyper_grid) const = 0;
  //
  // mutators
  virtual double insert_element(double element) = 0;
  virtual double remove_element(double element) = 0;
  virtual double incorporate_hyper_update() = 0;
  //
  // helpers
  friend std::ostream& operator<<(std::ostream& os, const ComponentModel &cm);
  // make protected later
  std::map<std::string, double> *p_hypers;
  std::string to_string();
 protected:
  int count;
  std::map<std::string, double> suffstats;
  double log_Z_0;
  double score;
  //
  // helpers
  virtual void set_log_Z_0() = 0;
  virtual void init_suffstats() = 0;
 private:
};

#endif // GUARD_componentmodel_h
