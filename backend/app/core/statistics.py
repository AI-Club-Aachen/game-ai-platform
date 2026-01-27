import numpy as np
'''
from backend.app.models.statistics import Player

# -----------------------------
# Utility: simple winrate
# -----------------------------

def calculate_winrate(player: Player) -> Player:
    total = player.wins + player.losses
    if total == 0:
        player.elo = 0.0
    else:
        player.elo = round(player.wins / total, 4)
    return player
'''

# -----------------------------
# Glicko-2 core functions
# -----------------------------

def g(phi):
    """Discount factor"""
    return 1.0 / np.sqrt(1.0 + 3.0 * phi**2 / np.pi**2)


def E(mu, mu_j, phi_j):
    """Expected score"""
    return 1.0 / (1.0 + np.exp(-g(phi_j) * (mu - mu_j)))


def compute_variance(mu, opp_mus, opp_phis):
    """Step 3: estimated variance"""
    v_inv = 0.0
    for mu_j, phi_j in zip(opp_mus, opp_phis):
        E_ = E(mu, mu_j, phi_j)
        v_inv += (g(phi_j)**2) * E_ * (1.0 - E_)
    return 1.0 / v_inv


def compute_delta(mu, opp_mus, opp_phis, scores, v):
    """Step 4: rating change"""
    delta_sum = 0.0
    for mu_j, phi_j, s_j in zip(opp_mus, opp_phis, scores):
        delta_sum += g(phi_j) * (s_j - E(mu, mu_j, phi_j))
    return v * delta_sum


# -----------------------------
# Volatility update (Algorithm 5)
# -----------------------------

def volatility_update(phi, delta, v, sigma, tau, eps=1e-6):
    a = np.log(sigma**2)

    def f(x):
        ex = np.exp(x)
        num = ex * (delta**2 - phi**2 - v - ex)
        den = 2.0 * (phi**2 + v + ex)**2
        return num / den - (x - a) / (tau**2)

    # Initial bounds
    A = a
    if delta**2 > phi**2 + v:
        B = np.log(delta**2 - phi**2 - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fA = f(A)
    fB = f(B)

    # Bisection
    while abs(B - A) > eps:
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)

        if fC * fB < 0:
            A = B
            fA = fB
        else:
            fA /= 2.0

        B = C
        fB = fC

    return np.exp(A / 2.0)


# -----------------------------
# Main Glicko-2 update
# -----------------------------

def glicko2_update(
    mu,
    phi,
    sigma,
    opp_mus,
    opp_phis,
    scores,
    tau
):
    # Step 3
    v = compute_variance(mu, opp_mus, opp_phis)

    # Step 4
    delta = compute_delta(mu, opp_mus, opp_phis, scores, v)

    # Step 5
    sigma_prime = volatility_update(phi, delta, v, sigma, tau)

    # Step 6
    phi_star = np.sqrt(phi**2 + sigma_prime**2)

    # Step 7
    phi_prime = 1.0 / np.sqrt(1.0 / phi_star**2 + 1.0 / v)

    mu_sum = 0.0
    for mu_j, phi_j, s_j in zip(opp_mus, opp_phis, scores):
        mu_sum += g(phi_j) * (s_j - E(mu, mu_j, phi_j))

    mu_prime = mu + phi_prime**2 * mu_sum

    return mu_prime, phi_prime, sigma_prime

def test_glicko2_canonical():
    # Conversion constants
    SCALE = 173.7178

    # Initial player
    R = 1500
    RD = 200
    sigma = 0.06
    tau = 0.5

    mu = (R - 1500) / SCALE
    phi = RD / SCALE

    # Opponents
    opp_R = np.array([1400, 1550, 1700])
    opp_RD = np.array([30, 100, 300])
    scores = np.array([1.0, 0.0, 0.0])

    opp_mus = (opp_R - 1500) / SCALE
    opp_phis = opp_RD / SCALE

    mu_p, phi_p, sigma_p = glicko2_update(
        mu, phi, sigma,
        opp_mus, opp_phis,
        scores,
        tau
    )

    # Convert back to Elo
    R_p = mu_p * SCALE + 1500
    RD_p = phi_p * SCALE

    print(f"Rating: {R_p:.2f}")
    print(f"RD:     {RD_p:.2f}")
    print(f"Sigma:  {sigma_p:.5f}")

    assert abs(R_p - 1464.06) < 0.1
    assert abs(RD_p - 151.52) < 0.1
    assert abs(sigma_p - 0.05999) < 1e-4

test_glicko2_canonical()