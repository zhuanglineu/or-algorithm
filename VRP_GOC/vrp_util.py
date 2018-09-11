from vrp_model import SeqInfo
from vrp_constant import *
from vrp_cost import calculate_each_cost

from itertools import permutations
import random


def generate_seq_info(seq, param, vehicle_type=-1):
    """
    generate a SeqInfo for a sequence
    :param seq:
    :param param:
    :param vehicle_type:
    :return:
    """
    ds, tm, volume, weight, first, last, ntj, position = param

    is_type2 = True if vehicle_type == 2 else False
    volume_limit = VOLUME_2 if is_type2 else VOLUME_1
    weight_limit = WEIGHT_2 if is_type2 else WEIGHT_1
    distance_limit = DISTANCE_2 if is_type2 else DISTANCE_1

    is_delivery, is_pickup, is_charge = ntj

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
    eps = 0         # early possible starting
    lps = 960       # latest possible starting
    total_wait = 0
    total_shift = 0
    total_delta = 0
    time_len = 0
    charge_cnt = 0

    for i in range(len(seq)):
        node2 = seq[i: i + 1]

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
            lps = max(first[node2], lps)

        total_delta += max(
            0, first[node2] - eps - serve_time - tm[node1, node2]
        )

        eps = max(eps + serve_time + tm[node1, node2], first[node2])
        time_len += tm[node1, node2] + serve_time + wait

        if is_charge(node2[0]):
            charge_cnt += 1

        serve_time = 30
        node1 = node2

    # get back to depot
    time_len += SERVE_TIME + tm[node1, (0,)]
    current_distance += ds[node1, (0,)]

    es = 0 + total_delta - total_wait
    ls = 960 - total_shift
    ef = es + time_len
    lf = ls + time_len

    if current_distance > (charge_cnt + 1) * distance_limit or lf > 960:
        if is_type2 or current_distance > (charge_cnt + 1) * DISTANCE_2 \
                or lf > 960:
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
        vehicle_type, max_volume, max_weight,
        current_distance, time_len,
        es, ls, ef, lf, total_wait,
        charge_cnt, sum(calculate_each_cost(
            current_distance, vehicle_type, total_wait, charge_cnt
        ))
    )


def generate_seq_from_nodes(
        nodes, param, vehicle_type=-1,
        best_accept=True, probability=0.6
):
    """
    generate best of first seq from a node list
    if best_accept=True, best accept
    if probability=1, first accept
    otherwise, accept with probability
    :param nodes:
    :param param:
    :param vehicle_type:
    :param best_accept:
    :param probability:
    :return:
    """
    best_cost = M
    best_seq = None
    best_info = None
    for seq in permutations(nodes):
        info = generate_seq_info(
            nodes, param, vehicle_type=vehicle_type
        )
        if info is not None:
            if best_accept:
                if info.cost < best_cost:
                    best_seq, best_info = seq, info
                    best_cost = info.cost
            else:
                if random.random() < probability:
                    return seq, info
    if best_info is not None:
        return best_seq, best_info

