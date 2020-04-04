# -*- coding: utf-8 -*-
"""
Created on Mon Jun  5 16:56:13 2017

@author: edgar
"""

from sharc.support.enumerations import StationType
from sharc.propagation.propagation import Propagation
from sharc.propagation.propagation_free_space import PropagationFreeSpace

import numpy as np
import matplotlib.pyplot as plt

class PropagationTvro(Propagation):
    """
    Implements the propagation model used in paper
    Fernandes, Linhares, "Coexistence conditions of LTE-advanced at 3400-3600MHz with TVRO
                          at 3625-4200 MHz in Brazil", Wireless Networks, 2017
    TODO: calculate the effective environment height for the generic case
    """

    def __init__(self, 
                 random_number_gen: np.random.RandomState,
                 environment : str):
        super().__init__(random_number_gen)
        if environment.upper() == "URBAN":
            self.d_k = 0.02 #km
            self.shadowing_std = 6
            self.h_a = 20
        elif environment.upper() == "SUBURBAN":
            self.d_k = 0.025 #km
            self.shadowing_std = 8
            self.h_a = 9
        self.building_loss = 20

        self.free_space_path_loss = PropagationFreeSpace(random_number_gen)

    def get_loss(self, *args, **kwargs) -> np.array:
        """
        Calculates path loss

        Parameters
        ----------
            distance_3D (np.array) : 3D distances between stations
            distance_2D (np.array) : 2D distances between stations
            frequency (np.array) : center frequencie [MHz]
            bs_height (np.array) : base station antenna heights
        Returns
        -------
            array with path loss values with dimensions of distance_2D

        """
        d_3D = kwargs["distance_3D"]
        f_MHz = kwargs["frequency"]
        f_GHz = f_MHz / 1000
        # shadowing is enabled by default
        shadowing = kwargs.pop("shadowing", True)
        number_of_sectors = kwargs.pop("number_of_sectors",1)
        indoor_stations = kwargs["indoor_stations"]
        if "imt_sta_type" in kwargs.keys():
            # calculating path loss for the IMT-system link
            height = kwargs["es_z"]
        else:
            # calculating path loss for the IMT-IMT link
            height = kwargs["ue_height"]

        free_space_path_loss = self.free_space_path_loss.get_loss(distance_3D=d_3D, frequency=f_MHz)

        f_fc = .25 + .375*(1 + np.tanh(7.5*(f_GHz-.5)))
        clutter_loss = 10.25 * f_fc * np.exp(-self.d_k) * \
                       (1 - np.tanh(6*(height/self.h_a - .625))) - .33

        loss = free_space_path_loss.copy()

        indices = (d_3D >= 40) & (d_3D < 10 * self.d_k * 1000)
        loss[indices] = loss[indices] + (d_3D[indices]/1000 - 0.04)/(10*self.d_k - 0.04) * clutter_loss[indices]

        indices = (d_3D >= 10 * self.d_k * 1000)
        loss[indices] = loss[indices] + clutter_loss[indices]

        loss = loss + self.building_loss*indoor_stations

        if shadowing:
             shadowing_fading = self.random_number_gen.normal(0, 
                                                              self.shadowing_std, 
                                                              loss.shape)
             loss = loss + shadowing_fading

        loss = np.maximum(loss, free_space_path_loss)

        if number_of_sectors > 1:
            loss = np.repeat(loss, number_of_sectors, 1)

        return loss

if __name__ == '__main__':
    shadowing_std = False
    distance_2D = np.linspace(10, 1000, num=1000)[:,np.newaxis]
    frequency = 3600*np.ones(distance_2D.shape)
    h_bs = 25*np.ones(len(distance_2D[:,0]))
    h_ue = 1.5*np.ones(len(distance_2D[0,:]))
    h_tvro = 6
    distance_3D = np.sqrt(distance_2D**2 + (h_bs[:,np.newaxis] - h_ue)**2)
    indoor_stations = np.zeros(distance_3D.shape, dtype = bool)
    shadowing = False

    rand_gen = np.random.RandomState(101)
    prop_urban = PropagationTvro(rand_gen, "URBAN")
    prop_suburban = PropagationTvro(rand_gen, "SUBURBAN")
    prop_free_space = PropagationFreeSpace(rand_gen)

    loss_urban_ue = prop_urban.get_loss(distance_3D = distance_3D, 
                                        frequency = frequency,
                                        indoor_stations = indoor_stations,
                                        shadowing = shadowing,
                                        ue_height = h_ue)
    loss_suburban_ue = prop_suburban.get_loss(distance_3D = distance_3D, 
                                              frequency = frequency,
                                              indoor_stations = indoor_stations,
                                              shadowing = shadowing,
                                              ue_height = h_ue)
    
    loss_urban_tvro = prop_urban.get_loss(distance_3D = distance_3D, 
                                          frequency = frequency,
                                          indoor_stations = indoor_stations,
                                          shadowing = shadowing,
                                          imt_sta_type = StationType.IMT_UE,
                                          es_z = h_tvro)
    loss_suburban_tvro = prop_suburban.get_loss(distance_3D = distance_3D, 
                                                frequency = frequency,
                                                indoor_stations = indoor_stations,
                                                shadowing = shadowing,
                                                imt_sta_type = StationType.IMT_UE,
                                                es_z = h_tvro)    
    
    loss_fs = prop_free_space.get_loss(distance_3D = distance_3D, 
                                       frequency = frequency)
    
    fig = plt.figure(figsize=(7,5), facecolor='w', edgecolor='k')
    ax = fig.gca()

    ax.semilogx(distance_3D, loss_urban_tvro, "-r", label = "urban, BS-to-TVRO", linewidth = 1)
    ax.semilogx(distance_3D, loss_suburban_tvro, "--r", label = "suburban, BS-to-TVRO", linewidth = 1)
    ax.semilogx(distance_3D, loss_urban_ue, "-b", label = "urban, BS-to-UE", linewidth = 1)
    ax.semilogx(distance_3D, loss_suburban_ue, "--b", label = "suburban, BS-to-UE", linewidth = 1)
    ax.semilogx(distance_3D, loss_fs, "-g", label = "free space", linewidth = 1.5)

    plt.title("Path loss (no shadowing)")
    plt.xlabel("distance [m]")
    plt.ylabel("path loss [dB]")
    plt.xlim((distance_3D[0,0], distance_3D[-1,0]))
    plt.ylim((70, 130))
    plt.legend(loc="upper left")
    plt.tight_layout()
    plt.grid()

    plt.show()
