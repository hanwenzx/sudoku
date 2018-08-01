from __future__ import print_function
import random
import copy
import time
import subprocess


def to_cnf_unit(spot, value):
    a, b = spot
    loc = ((a - 1) * 9 + b - 1) * 9
    return str(loc + value)


def to_spot_value(cnf_unit):
    c = int(cnf_unit)
    if c % 9 == 0:
        value = 9
    else:
        value = c % 9
    c -= value
    b = ((c / 9) + 1) % 9
    if b == 0:
        b = 9
    if ((c / 9) + 1) % 9 == 0:
        a = ((c / 9) + 1) / 9
    else:
        a = ((c / 9) + 1) / 9 + 1
    return (int(a), int(b), value)


class Grid:
    def __init__(self, problem):
        self.spots = [(i, j) for i in range(1, 10) for j in range(1, 10)]
        self.domains = {}
        # Need a dictionary that maps each spot to its related spots
        self.peers = {}
        self.parse(problem)

    def parse(self, problem):
        for i in range(0, 9):
            for j in range(0, 9):
                c = problem[i * 9 + j]
                if c == '.':
                    self.domains[(i + 1, j + 1)] = range(1, 10)
                else:
                    self.domains[(i + 1, j + 1)] = [ord(c) - 48]

    def display(self):
        for i in range(0, 9):
            for j in range(0, 9):
                d = self.domains[(i + 1, j + 1)]
                if len(d) == 1:
                    print(d[0], end='')
                else:
                    print('.', end='')
                if j == 2 or j == 5:
                    print(" | ", end='')
            print()
            if i == 2 or i == 5:
                print("---------------")


class Solver3:
    def __init__(self, grid):
        # sigma is the assignment function
        self.sigma = {}
        self.grid = grid
        for spot in self.grid.spots:
            self.grid.peers[spot] = self.get_peers(spot)
        # copy given assignments to sigma
        for spot in grid.domains.keys():
            if len(grid.domains[spot]) == 1:
                self.sigma[spot] = grid.domains[spot][0]

    def solve(self):
        self.output_cnf()
        picosat = subprocess.Popen(['./picosat/picosat', 'out.cnf'], stdout=subprocess.PIPE)
        output = picosat.communicate()[0]
        positives = [int(s) for s in output.split() if s.isdigit()][:-1]
        assert len(positives) == 81
        for u in positives:
            (a, b, value) = to_spot_value(u)
            self.grid.domains[(a, b)] = [value]
        return True

    def get_peers(self, ab):
        a, b = ab
        peers_set = set([])
        for i in range(1, 10):
            peers_set.add((i, b))
            peers_set.add((a, i))
            pass
        start_a = int((a - 1)/3) * 3 + 1
        start_b = int((b - 1)/3) * 3 + 1
        for k in range(3):
            for l in range(3):
                peers_set.add((start_a + k, start_b + l))
        peers_list = list(peers_set)
        peers_list.remove((a, b))
        return peers_list

    def output_cnf(self):
        f = open("out.cnf", "w")
        clause_count = 7371 + len([k for k in self.grid.domains.keys() if len(self.grid.domains[k]) == 1])
        # first line
        f.write(f"p cnf 729 {clause_count}\n")
        # grid items
        for spot in self.grid.domains.keys():
            if len(self.grid.domains[spot]) == 1:
                f.write(to_cnf_unit(spot, self.grid.domains[spot][0]) + " 0\n")
        # line 19-81
        count = 1
        for i in range(81):
            s = ""
            for j in range(9):
                s += str(count) + " "
                count += 1
            s += "0\n"
            f.write(s)
        # 82 and beyond
        for spot in self.grid.domains.keys():
            for peer in self.grid.peers[spot]:
                for value in range(1, 10):
                    x1 = to_cnf_unit(spot, value)
                    x2 = to_cnf_unit(peer, value)
                    if x1 < x2:
                        f.write(f"-{x1} -{x2} 0\n")
        f.close()


class Solver:
    def __init__(self, grid):
        # sigma is the assignment function
        self.sigma = {}
        self.grid = grid
        for spot in self.grid.spots:
            self.grid.peers[spot] = self.get_peers(spot)
        # copy given assignments to sigma
        for spot in grid.domains.keys():
            if len(grid.domains[spot]) == 1:
                self.sigma[spot] = grid.domains[spot][0]

    def solve(self):
        result = self.search(self.sigma)
        if result:
            for s1 in result.keys():
                self.grid.domains[s1] = [result[s1]]
            return True
        return False

    # generate peers for a spot
    def get_peers(self, ab):
        a, b = ab
        peers_set = set([])
        for i in range(1, 10):
            peers_set.add((i, b))
            peers_set.add((a, i))
            pass
        start_a = int((a - 1)/3) * 3 + 1
        start_b = int((b - 1)/3) * 3 + 1
        for k in range(3):
            for l in range(3):
                peers_set.add((start_a + k, start_b + l))
        peers_list = list(peers_set)
        peers_list.remove((a, b))
        return peers_list

    def search(self, sigma):
        unassigned = [i for i in self.grid.spots if i not in sigma]
        if len(sigma.keys()) == 81:
            return sigma
        for spot in unassigned:
            for value in self.grid.domains[spot]:
                sigma2 = copy.deepcopy(sigma)
                if self.consistent(spot, value, sigma):
                    sigma[spot] = value
                    if self.infer1(spot, sigma):
                        result = self.search(sigma)
                        if result is not None:
                            return result
                sigma = sigma2
            return None
        return None

    # return true iff spot and value fits
    def consistent(self, spot, value, sigma):
        (a, b) = spot
        for i in range(1, 10):
            if (a, i) in sigma.keys():
                if sigma[(a, i)] == value:
                    return False
            if (i, b) in sigma.keys():
                if sigma[(i, b)] == value:
                    return False
        start_a = int((a - 1)/3) * 3 + 1
        start_b = int((b - 1)/3) * 3 + 1
        for i in range(3):
            for j in range(3):
                if (start_a + i, start_b + j) not in sigma.keys():
                    continue
                if sigma[start_a + i, start_b + j] == value:
                    return False
        return True

    def infer1(self, spot, sigma):
        # store possible values
        local_domain = {}
        # set empty spot's possibles values 1-9
        for peer in self.grid.peers[spot]:
            if peer not in sigma:
                local_domain[peer] = list(range(1, 10))
        for s in local_domain.keys():
            for p in self.grid.peers[s]:
                if p in sigma and sigma[p] in local_domain[s]:
                    local_domain[s].remove(sigma[p])
                if len(local_domain[s]) == 0:
                    return False
            if len(local_domain[s]) == 1:
                sigma[s] = local_domain[s][0]
                for i in self.grid.peers[s]:
                    if i in local_domain.keys():
                        if sigma[s] in local_domain[i]:
                            local_domain[i].remove(sigma[s])
                self.infer1(s, sigma)
        return True


class Solver2:
    def __init__(self, grid):
        # sigma is the assignment function
        self.sigma = {}
        self.grid = grid
        for spot in self.grid.spots:
            self.grid.peers[spot] = self.get_peers(spot)
        for spot in grid.domains.keys():
            if len(grid.domains[spot]) == 1:
                self.grid.domains = self.eliminate_peers(self.grid.domains, spot, self.grid.domains[spot][0])
        # copy given assignments to sigma
        for spot in grid.domains.keys():
            if len(grid.domains[spot]) == 1:
                self.sigma[spot] = grid.domains[spot][0]

    # elminate a single value in a spot
    def eliminate(self, domains, spot, value):
        if domains is False:
            return False
        #print(f"Elim {value} at {spot}")
        if value not in domains[spot]:
            return domains
        domains[spot] = list(domains[spot])
        domains[spot].remove(value)
        #print(domains[spot])
        if len(domains[spot]) == 0:
            return False
        elif len(domains[spot]) == 1:
            v2 = domains[spot][0]
            #print(f"Elim set {v2} at {spot}")
            for p2 in self.grid.peers[spot]:
                domains = self.eliminate(domains, p2, v2)
        return domains

    # elminate values for all peers
    def eliminate_peers(self, domains, spot, value):
        domains = copy.deepcopy(domains)
        for peer in self.grid.peers[spot]:
            if domains is False:
                return False
            domains = self.eliminate(domains, peer, value)
        return domains

    def solve(self):
        result = self.search2(self.grid.domains, self.sigma)
        if result:
            for s1 in result.keys():
                self.grid.domains[s1] = [result[s1]]
            return True
        return False

    def get_peers(self, ab):
        a, b = ab
        peers_set = set([])
        for i in range(1, 10):
            peers_set.add((i, b))
            peers_set.add((a, i))
            pass
        start_a = int((a - 1)/3) * 3 + 1
        start_b = int((b - 1)/3) * 3 + 1
        for k in range(3):
            for l in range(3):
                peers_set.add((start_a + k, start_b + l))
        peers_list = list(peers_set)
        peers_list.remove((a, b))
        return peers_list

    def search2(self, domains, sigma):
        unassigned = [i for i in self.grid.spots if i not in sigma]
        unassigned = [k for k in sorted(unassigned, key=lambda k: len(domains[k]))]
        if len(sigma.keys()) == 81:
            return sigma
        for spot in unassigned:
            for value in domains[spot]:
                sigma2 = copy.deepcopy(sigma)
                domains2 = copy.deepcopy(domains)
                if self.consistent(spot, value, sigma):
                    sigma[spot] = value
                    domains = self.eliminate_peers(domains, spot, value)
                    if self.infer1(spot, sigma) and domains:
                        result = self.search2(domains, sigma)
                        if result is not None:
                            return result
                sigma = sigma2
                domains = domains2
            return None
        return None

    def consistent(self, spot, value, sigma):
        (a, b) = spot
        for i in range(1, 10):
            if (a, i) in sigma.keys():
                if sigma[(a, i)] == value:
                    return False
            if (i, b) in sigma.keys():
                if sigma[(i, b)] == value:
                    return False
        start_a = int((a - 1)/3) * 3 + 1
        start_b = int((b - 1)/3) * 3 + 1
        for i in range(3):
            for j in range(3):
                if (start_a + i, start_b + j) not in sigma.keys():
                    continue
                if sigma[start_a + i, start_b + j] == value:
                    return False
        return True

    def infer1(self, spot, sigma):
        # store possible values
        local_domain = {}
        # set empty spot's possibles values 1-9
        for peer in self.grid.peers[spot]:
            if peer not in sigma:
                local_domain[peer] = list(range(1, 10))
        for s in local_domain.keys():
            for p in self.grid.peers[s]:
                if p in sigma and sigma[p] in local_domain[s]:
                    local_domain[s].remove(sigma[p])
                if len(local_domain[s]) == 0:
                    return False
            if len(local_domain[s]) == 1:
                sigma[s] = local_domain[s][0]
                for i in self.grid.peers[s]:
                    if i in local_domain.keys():
                        if sigma[s] in local_domain[i]:
                            local_domain[i].remove(sigma[s])
                self.infer1(s, sigma)
        return True

test_infer = [".346.891267219.348198.425.785..614234......917139.485696153728428741963534528617."]

easy = [
    "..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3..",
    "2...8.3...6..7..84.3.5..2.9...1.54.8.........4.27.6...3.1..7.4.72..4..6...4.1...3"]

hard = [
    "4.....8.5.3..........7......2.....6.....8.4......1.......6.3.7.5..2.....1.4......",
    "52...6.........7.13...........4..8..6......5...........418.........3..2...87....."]

print("====Problem====")
g = Grid(hard[1])
# Display the original problem
g.display()
t0 = time.time()
s = Solver2(g)
if s.solve():
    print("====Solution===")
    # Display the solution
    # Feel free to call other functions to display
    g.display()
    print(f"Solved in {time.time()-t0}s")
else:
    print("==No solution==")
