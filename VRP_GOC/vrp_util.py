from vrp_model import SeqInfo
from vrp_constant import *
from vrp_cost import calculate_each_cost

from functools import reduce


def schedule_time(seq, tm, first, last):
    node1 = (0,)
    serve_time = 0
    eps = 0  # early possible starting
    lps = 960  # latest possible starting
    total_wait = 0
    total_shift = 0
    total_delta = 0
    time_len = 0
    for i in range(len(seq)):
        node2 = seq[i:i + 1]

        if node1 == node2:
            return None, None, None, None, None, None

        shift = max(0, lps + tm[node1, node2] + serve_time - last[node2])

        # lps = lps_node2
        if shift > 0:
            lps = last[node2]
            total_shift += shift
        else:
            lps += tm[node1, node2] + serve_time

        # check: if lps_node1 < eps_node1, return None 
        if lps - tm[node1, node2] - serve_time < eps:
            return None, None, None, None, None, None

        # update wait and lps_node2
        wait = max(0, first[node2] - lps)
        if wait > 0:
            total_wait += wait
            lps = max(first[node2], lps)

        # eps = eps_node2
        total_delta += max(0,
                           first[node2] - eps - serve_time - tm[node1, node2])
        eps = max(eps + serve_time + tm[node1, node2], first[node2])

        # time_len += tm + serve + wait
        time_len += tm[node1, node2] + serve_time + wait

        # iter
        serve_time = SERVE_TIME
        node1 = node2

    time_len += SERVE_TIME + tm[node1, (0,)]  # back to depot

    es = 0 + total_delta - total_wait
    ls = 960 - total_shift
    ef = es + time_len
    lf = ls + time_len
    return time_len, es, ls, ef, lf, total_wait


def generate_seq_info(
        seq, ds, tm, volume, weight, first, last,
        node_type_judgement, vehicle_type=-1
):
    if vehicle_type == -1 or vehicle_type == 1:
        volume_limit = VOLUME_1
        weight_limit = WEIGHT_1
        distance_limit = DISTANCE_1
        must_be_type2 = False
    else:
        volume_limit = VOLUME_2
        weight_limit = WEIGHT_2
        distance_limit = DISTANCE_2
        must_be_type2 = True

    is_delivery, is_pickup, is_charge = node_type_judgement

    # init volume and weight
    delivery_node = list(filter(lambda x: is_delivery(x), seq))
    # charge_cnt = sum(filter(lambda x: is_charge(x), seq))
    init_volume = sum([volume[(x,)] for x in delivery_node])
    init_weight = sum([weight[(x,)] for x in delivery_node])

    current_volume = init_volume
    current_weight = init_weight

    if current_volume > volume_limit or current_weight > weight_limit:
        if current_volume > VOLUME_2 or current_weight > WEIGHT_2:
            return None
        else:
            must_be_type2 = True
            volume_limit = VOLUME_2
            weight_limit = WEIGHT_2
            distance_limit = DISTANCE_2

    # first node
    node1 = (0,)
    current_distance = 0
    max_volume = init_volume
    max_weight = init_weight
    serve_time = 0
    eps = 0  # early possible starting
    lps = 960  # latest possible starting
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

        if current_volume > volume_limit or current_weight > weight_limit or \
                current_distance > (charge_cnt + 1) * distance_limit or \
                lps - tm[node1, node2] - serve_time < eps:
            if must_be_type2:
                return None
            else:
                if current_volume > VOLUME_2 or current_weight > WEIGHT_2 or \
                        current_distance > (charge_cnt + 1) * DISTANCE_2 or \
                        lps - tm[node1, node2] - serve_time < eps:
                    return None
                else:
                    must_be_type2 = True
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

        # iter
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
        if must_be_type2 or current_distance > (charge_cnt + 1) * DISTANCE_2 \
                or lf > 960:
            return None
        else:
            must_be_type2 = True

    # choose vehicle type
    if vehicle_type == -1:
        if must_be_type2 or max_volume > VOLUME_1 or max_weight > WEIGHT_1 or \
                current_distance > (charge_cnt + 1) * DISTANCE_1:
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


def calculate_seq_position(seq, position):
    return reduce(
        lambda x, y: (x[0] + y[0], x[1] + y[1]),
        [position[x] for x in seq]
    )


def calculate_distance(seq1, seq2, position_dict):
    p1 = position_dict[seq1]
    p2 = position_dict[seq2]
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def get_neighborhood_dict(route_dict, position, neighborhood_number=10):
    seq_list = list(route_dict.keys())
    position_dict = {
        seq: calculate_seq_position(seq, position)
        for seq in seq_list
    }
    neighborhood_dict = dict()
    for seq in seq_list:
        compare_list = [
            (comp, calculate_distance(seq, comp, position_dict))
            for comp in seq_list if comp != seq
        ]
        compare_list.sort(key=lambda x: x[-1])
        neighborhood_dict[seq] = [
            x[0] for x in compare_list[:neighborhood_number]
        ]
    return neighborhood_dict
