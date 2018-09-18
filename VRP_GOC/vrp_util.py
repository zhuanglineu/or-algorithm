from vrp_model import SeqInfo, Param
from vrp_cost import calculate_each_cost
from vrp_constant import *

import random
from itertools import permutations
from typing import Tuple, List


def calculate_seq_distance(
        seq: Tuple,
        param: Param
) -> (float, List[float]):
    ds, *_, ntj, _ = param
    *_, is_charge = ntj
    charge_index = [i for i in range(len(seq)) if is_charge(seq[i])]
    i = 0
    tmp_seq = (0, *seq, 0)
    dist_list = []
    for j in (x+1 for x in charge_index):
        sub_seq = tmp_seq[i:j+1]
        dist = 0
        # calculate sub_seq
        node0 = sub_seq[:1]
        for node1 in ((x, ) for x in sub_seq[1:]):
            dist += ds[node0, node1]
            node0 = node1
        dist_list.append(dist)
        i = j
    sub_seq = tmp_seq[i:]
    dist = 0
    node0 = sub_seq[:1]
    for node1 in ((x,) for x in sub_seq[1:]):
        dist += ds[node0, node1]
        node0 = node1
    dist_list.append(dist)

    return sum(dist_list), dist_list


def generate_seq_info(
        seq: Tuple[int],
        param: Param,
        vehicle_type: int = -1
) -> SeqInfo:
    """
    generate a SeqInfo for a sequence
    :param seq:
    :param param:
    :param vehicle_type:
    :return:
    """
    ds, tm, volume, weight, first, last, ntj, position = param
    is_delivery, is_pickup, is_charge = ntj

    is_type2 = True if vehicle_type == 2 else False
    volume_limit = VOLUME_2 if is_type2 else VOLUME_1
    weight_limit = WEIGHT_2 if is_type2 else WEIGHT_1
    distance_limit = DISTANCE_2 if is_type2 else DISTANCE_1

    charge_index = [i for i in range(len(seq)) if is_charge(seq[i])]

    # init volume and weight
    delivery_node = list(filter(lambda x: is_delivery(x), seq))
    init_volume = sum([volume[(x,)] for x in delivery_node])
    init_weight = sum([weight[(x,)] for x in delivery_node])

    current_volume = init_volume
    current_weight = init_weight

    if current_volume > volume_limit or current_weight > weight_limit:
        if is_type2 or current_volume > VOLUME_2 or current_weight > WEIGHT_2:
            return None
        else:
            is_type2 = True
            volume_limit = VOLUME_2
            weight_limit = WEIGHT_2
            distance_limit = DISTANCE_2

    # first node
    node1 = (0,)
    current_distance = 0
    max_volume = init_volume
    max_weight = init_weight
    serve_time = 0
    eps = 0  # earliest possible starting
    lps = 960  # latest possible starting
    total_wait = 0
    total_shift = 0
    total_delta = 0
    time_len = 0
    charge_cnt = 0

    # init eps_list and lps_list
    eps_list = [0]
    lps_list = [960]

    for node2 in ((nid,) for nid in seq):

        # distance
        current_distance += ds[node1, node2]

        # volume and weight
        if is_delivery(node2[0]):
            current_volume -= volume[node2]
            current_weight -= weight[node2]
        elif is_pickup(node2[0]):
            current_volume += volume[node2]
            current_weight += weight[node2]
            max_volume = max(max_volume, current_volume)
            max_weight = max(max_weight, current_weight)

        # time window
        shift = max(0, lps + tm[node1, node2] + serve_time - last[node2])
        if shift > 0:
            lps = last[node2]
            total_shift += shift
        else:
            lps += tm[node1, node2] + serve_time

        if max_volume > volume_limit or max_weight > weight_limit or \
                current_distance > (charge_cnt + 1) * distance_limit or \
                lps - tm[node1, node2] - serve_time < eps:
            if is_type2:
                return None
            else:
                if max_volume > VOLUME_2 or max_weight > WEIGHT_2 or \
                        current_distance > (charge_cnt + 1) * DISTANCE_2 or \
                        lps - tm[node1, node2] - serve_time < eps:
                    return None
                else:
                    is_type2 = True
                    volume_limit = VOLUME_2
                    weight_limit = WEIGHT_2
                    distance_limit = DISTANCE_2

        wait = max(0, first[node2] - lps)
        if wait > 0:
            total_wait += wait
            lps = first[node2]

        delta = max(
            0, first[node2] - eps - serve_time - tm[node1, node2]
        )
        total_delta += delta

        # eps: eps_node2
        eps = max(eps + serve_time + tm[node1, node2], first[node2])

        # update eps_list and lps_list
        if delta > 0 or wait > 0:
            eps_list = [x + delta - wait for x in eps_list]
        if shift > 0:
            lps_list = [x - shift for x in lps_list]
        eps_list.append(eps)
        lps_list.append(lps)

        # time_len += tm + serve + wait
        time_len += tm[node1, node2] + serve_time + wait

        if is_charge(node2[0]):
            charge_cnt += 1

        serve_time = 30
        node1 = node2

    # get back to depot
    time_len += SERVE_TIME + tm[node1, (0,)]
    current_distance += ds[node1, (0,)]

    eps_list.append(0 + total_delta - total_wait + time_len)
    lps_list.append(960 - total_shift + time_len)
    buffer = lps_list[0] - eps_list[0]

    if current_distance > (charge_cnt + 1) * distance_limit \
            or lps_list[-1] > 960:
        if is_type2 or current_distance > (charge_cnt + 1) * DISTANCE_2 \
                or lps_list[-1] > 960:
            return None
        else:
            is_type2 = True

    # choose vehicle type
    if vehicle_type == -1:
        if is_type2:
            vehicle_type = 2
        else:
            vehicle_type = 1

    return SeqInfo(
        vehicle_type, max_volume, max_weight, current_distance,
        eps_list, lps_list, time_len, total_wait, buffer,
        charge_index, sum(calculate_each_cost(
            current_distance, vehicle_type, total_wait, charge_cnt
        ))
    )


def generate_seq_from_nodes(
        nodes: List[int],
        param: Param,
        vehicle_type: int = -1,
        best_accept: bool = True,
        better_accept: bool = True,
        probability: float = 0.6
) -> (Tuple, SeqInfo):
    """
    generate best of first seq from a node list
    if best_accept=True, best accept
    if probability=1, first accept
    otherwise, accept with probability
    :param nodes:
    :param param:
    :param vehicle_type:
    :param best_accept:
    :param better_accept:
    :param probability:
    :return:
    """
    better_accept = False if best_accept else better_accept
    probability = 0 if better_accept or best_accept else probability
    tmp_cost = M
    tmp_seq = None
    tmp_info = None
    for new_seq in permutations(nodes):
        new_info = generate_seq_info(new_seq, param, vehicle_type=vehicle_type)
        if new_info is None:
            continue
        else:
            if new_info.cost < tmp_cost:
                if best_accept:
                    tmp_seq = new_seq
                    tmp_info = new_info
                    tmp_cost = new_info.cost
                    continue
                if better_accept:
                    return new_seq, new_info
            if probability and random.random() < probability:
                return new_seq, new_info
    if tmp_seq is None:
        return None, None
    else:
        return tmp_seq, tmp_info
