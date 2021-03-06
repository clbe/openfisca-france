# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


from __future__ import division

from numpy import (maximum as max_, minimum as min_)
from openfisca_core.accessors import law

from .base import QUIFAM, QUIFOY, QUIMEN


CHEF = QUIFAM['chef']
CONJ = QUIFOY['conj']
PART = QUIFAM['part']
PREF = QUIMEN['pref']
VOUS = QUIFOY['vous']


# 1 ACTIF BRUT


def _isf_imm_bati(b1ab, b1ac, P = law.isf.res_princ):
    '''
    Immeubles bâtis
    '''
    return (1 - P.taux) * b1ab + b1ac


def _isf_imm_non_bati(b1bc, b1be, b1bh, b1bk, P = law.isf.nonbat):
    '''
    Immeubles non bâtis
    '''
    # forêts
    b1bd = b1bc * P.taux_f
    # bien ruraux loués à long terme
    b1bf = min_(b1be, P.seuil) * P.taux_r1
    b1bg = max_(b1be - P.seuil, 0) * P.taux_r2
    # part de groupements forestiers- agricoles fonciers
    b1bi = min_(b1bh, P.seuil) * P.taux_r1
    b1bj = max_(b1bh - P.seuil, 0) * P.taux_r2
    return b1bd + b1bf + b1bg + b1bi + b1bj + b1bk


# # droits sociaux- valeurs mobilières- liquidités- autres meubles ##


def _isf_actions_sal(b1cl, P = law.isf.droits_soc):  # # non présent en 2005##
    '''
    Parts ou actions détenues par les salariés et mandataires sociaux
    '''
    return  b1cl * P.taux1


def _isf_droits_sociaux(isf_actions_sal, b1cb, b1cd, b1ce, b1cf, b1cg, P = law.isf.droits_soc):
    # parts ou actions de sociétés avec engagement de 6 ans conservation minimum
    b1cc = b1cb * P.taux2
    return isf_actions_sal + b1cc + b1cd + b1ce + b1cf + b1cg


def _ass_isf(isf_imm_bati, isf_imm_non_bati, isf_droits_sociaux, b1cg, b2gh, P = law.isf.forf_mob):
    '''
    TODO: Gérer les trois option meubles meublants
    '''
    total = isf_imm_bati + isf_imm_non_bati + isf_droits_sociaux
    forf_mob = (b1cg != 0) * b1cg + (b1cg == 0) * total * P.taux
    actif_brut = total + forf_mob
    return actif_brut - b2gh


# # calcul de l'impôt par application du barème ##


def _isf_iai_2011_(ass_isf, _P, bareme = law.isf.bareme):
    ass_isf = (ass_isf >= bareme.rates[1]) * ass_isf
    return bareme.calc(ass_isf)

def _isf_iai__2010(ass_isf, _P, bareme = law.isf.bareme):
    return bareme.calc(ass_isf)

def _isf_avant_reduction(isf_iai, decote_isf):
    return isf_iai - decote_isf


def _isf_reduc_pac(nb_pac, nbH, P = law.isf.reduc_pac):
    '''
    Réductions pour personnes à charges
    '''
    return P.reduc_1 * nb_pac + P.reduc_2 * nbH


def _isf_inv_pme(b2mt, b2ne, b2mv, b2nf, b2mx, b2na, P = law.isf.pme):
    '''
    Réductions pour investissements dans les PME
    à partir de 2008!
    '''
    inv_dir_soc = b2mt * P.taux2 + b2ne * P.taux1
    holdings = b2mv * P.taux2 + b2nf * P.taux1
    fip = b2mx * P.taux1
    fcpi = b2na * P.taux1
    return holdings + fip + fcpi + inv_dir_soc


def _isf_org_int_gen(b2nc, P = law.isf.pme):
    # TODO: rajouter ng (dons à certains organismes d'intérêt général)
    return b2nc * P.taux2


def _isf_avant_plaf(isf_avant_reduction, isf_inv_pme, isf_org_int_gen, isf_reduc_pac, borne_max = law.isf.pme.max):
    '''
    Montant de l'impôt avant plafonnement
    '''
    return max_(0, isf_avant_reduction - min_(isf_inv_pme + isf_org_int_gen, borne_max) - isf_reduc_pac)


# # calcul du plafonnement ##
def _tot_impot(self, irpp, isf_avant_plaf, crds_holder, csg_holder, prelsoc_cap_holder):
    '''
    Total des impôts dus au titre des revenus et produits (irpp, cehr, pl, prélèvements sociaux) + ISF
    Utilisé pour calculer le montant du plafonnement de l'ISF
    '''
    crds = self.split_by_roles(crds_holder, roles = [VOUS, CONJ])
    csg = self.split_by_roles(csg_holder, roles = [VOUS, CONJ])
    prelsoc_cap = self.split_by_roles(prelsoc_cap_holder, roles = [VOUS, CONJ])

    return -irpp + isf_avant_plaf - (crds[VOUS] + crds[CONJ]) - (csg[VOUS] + csg[CONJ]) - (prelsoc_cap[VOUS] + prelsoc_cap[CONJ])

# irpp n'est pas suffisant : ajouter ir soumis à taux propor + impôt acquitté à l'étranger
# + prélèvement libé de l'année passée + montant de la csg TODO:


def _revetproduits(self, salcho_imp_holder, pen_net_holder, rto_net_holder, rev_cap_bar, fon, ric_holder, rag_holder,
        rpns_exon_holder, rpns_pvct_holder, rev_cap_lib, imp_lib, P = law.isf.plafonnement):
        # TODO: ric? benef indu et comm
    '''
    Revenus et produits perçus (avant abattement),
    Utilisé pour calculer le montant du plafonnement de l'ISF
    Cf. http://www.impots.gouv.fr/portal/deploiement/p1/fichedescriptiveformulaire_8342/fichedescriptiveformulaire_8342.pdf
    '''
    pen_net = self.sum_by_entity(pen_net_holder)
    rag = self.sum_by_entity(rag_holder)
    ric = self.sum_by_entity(ric_holder)
    rpns_exon = self.sum_by_entity(rpns_exon_holder)
    rpns_pvct = self.sum_by_entity(rpns_pvct_holder)
    rto_net = self.sum_by_entity(rto_net_holder)
    salcho_imp = self.sum_by_entity(salcho_imp_holder)

    # rev_cap et imp_lib pour produits soumis à prel libératoire- check TODO:
    # # def rev_exon et rev_etranger dans data? ##
    pt = max_(salcho_imp + pen_net + rto_net + rev_cap_bar + rev_cap_lib + ric + rag + rpns_exon + rpns_pvct + imp_lib + fon, 0)
    return pt * P.taux


def _decote_isf_2013_(ass_isf, _P, P = law.isf.decote):
    '''
    Décote d el'ISF
    '''
    elig = (ass_isf >= P.min) & (ass_isf <= P.max)
    LB = P.base - P.taux * ass_isf
    return LB * elig

def _isf_apres_plaf__2011(tot_impot, revetproduits, isf_avant_plaf, _P, P = law.isf.plaf):
    """
    Impôt sur la fortune après plafonnement
    """
    # # si ISF avant plafonnement n'excède pas seuil 1= la limitation du plafonnement ne joue pas ##
    # # si entre les deux seuils; l'allègement est limité au 1er seuil ##
    # # si ISF avant plafonnement est supérieur au 2nd seuil, l'allègement qui résulte du plafonnement est limité à 50% de l'ISF ##

    # Plafonnement supprimé pour l'année 2012
    plafonnement = max_(tot_impot - revetproduits, 0)
    limitationplaf = (
                      (isf_avant_plaf <= P.seuil1) * plafonnement +
                      (P.seuil1 <= isf_avant_plaf) * (isf_avant_plaf <= P.seuil2) * min_(plafonnement, P.seuil1) +
                      (isf_avant_plaf >= P.seuil2) * min_(isf_avant_plaf * P.taux, plafonnement))
    return max_(isf_avant_plaf - limitationplaf, 0)

def _isf_apres_plaf_2012(isf_avant_plaf, _P, P = law.isf.plaf):
    """
    Impôt sur la fortune après plafonnement
    """
    # # si ISF avant plafonnement n'excède pas seuil 1= la limitation du plafonnement ne joue pas ##
    # # si entre les deux seuils; l'allègement est limité au 1er seuil ##
    # # si ISF avant plafonnement est supérieur au 2nd seuil, l'allègement qui résulte du plafonnement est limité à 50% de l'ISF ##

    # Plafonnement supprimé pour l'année 2012

    return isf_avant_plaf


def _isf_apres_plaf_2013_(tot_impot, revetproduits, isf_avant_plaf, _P, P = law.isf.plaf):
    """
    Impôt sur la fortune après plafonnement
    """
    # # si ISF avant plafonnement n'excède pas seuil 1= la limitation du plafonnement ne joue pas ##
    # # si entre les deux seuils; l'allègement est limité au 1er seuil ##
    # # si ISF avant plafonnement est supérieur au 2nd seuil, l'allègement qui résulte du plafonnement est limité à 50% de l'ISF ##

    # Plafonnement supprimé pour l'année 2012

    plafond = max_(0, tot_impot - revetproduits)  # case PU sur la déclaration d'impôt
    return max_(isf_avant_plaf - plafond, 0)

def _isf_tot(b4rs, isf_avant_plaf, isf_apres_plaf, irpp):
    # # rs est le montant des impôts acquittés hors de France ##
    return min_(-((isf_apres_plaf - b4rs) * ((-irpp) > 0) + (isf_avant_plaf - b4rs) * ((-irpp) <= 0)), 0)


# # BOUCLIER FISCAL ##

# # calcul de l'ensemble des revenus du contribuable ##


# TODO: à reintégrer dans irpp
def _rvcm_plus_abat(rev_cat_rvcm, rfr_rvcm):
    '''
    Revenu catégoriel avec abattement de 40% réintégré.
    '''
    return rev_cat_rvcm + rfr_rvcm


# TODO: à reintégrer dans irpp (et vérifier au passage que frag_impo est dans la majo_cga
def _maj_cga(self, frag_impo, nrag_impg,
            nbic_impn, nbic_imps, nbic_defn, nbic_defs,
            nacc_impn, nacc_meup, nacc_defn, nacc_defs,
            nbnc_impo, nbnc_defi, P = law.ir.rpns):
    '''
    Majoration pour non adhésion à un centre de gestion agréé
    'foy'
    '''

    # # B revenus industriels et commerciaux professionnels
    nbic_timp = (nbic_impn + nbic_imps) - (nbic_defn + nbic_defs)

    # # C revenus industriels et commerciaux non professionnels
    # (revenus accesoires du foyers en nomenclature INSEE)
    nacc_timp = max_(0, (nacc_impn + nacc_meup) - (nacc_defn + nacc_defs))

    # regime de la déclaration contrôlée ne bénéficiant pas de l'abattement association agréée
    nbnc_timp = nbnc_impo - nbnc_defi

    # # Totaux
    ntimp = nrag_impg + nbic_timp + nacc_timp + nbnc_timp

    maj_cga = max_(0, P.cga_taux2 * (ntimp + frag_impo))
    return self.sum_by_entity(maj_cga)


def _bouclier_rev(rbg, maj_cga, csg_deduc, rvcm_plus_abat, rev_cap_lib, rev_exo, rev_or, cd_penali, cd_eparet):
    '''
    Total des revenus sur l'année 'n' net de charges
    '''
    # TODO: réintégrer les déficits antérieur
    # TODO: intégrer les revenus soumis au prélèvement libératoire
    null = 0 * rbg

    deficit_ante = null

    # # Revenus
    frac_rvcm_rfr = 0.7 * rvcm_plus_abat  # TODO: UNUSED ?
    # # revenus distribués?
    # # A majorer de l'abatt de 40% - montant brut en cas de PFL
    # # pour le calcul de droit à restitution : prendre 0.7*montant_brut_rev_dist_soumis_au_barème
    rev_bar = rbg - maj_cga - csg_deduc - deficit_ante

# # TODO: AJOUTER : indemnités de fonction percus par les élus- revenus soumis à régimes spéciaux

    # Revenu soumis à l'impôt sur le revenu forfaitaire
    rev_lib = rev_cap_lib
    # # AJOUTER plus-values immo et moins values?

    # #Revenus exonérés d'IR réalisés en France et à l'étranger##
#    rev_exo = primes_pel + primes_cel + rente_pea + int_livrets + plus_values_per
    rev_exo = null

    # # proposer à l'utilisateur des taux de réference- PER, PEA, PEL,...TODO
    # # sommes investis- calculer les plus_values annuelles et prendre en compte pour rev_exo?
    # revenus soumis à la taxe forfaitaire sur les métaux précieux : rev_or

    revenus = rev_bar + rev_lib + rev_exo + rev_or

    # # CHARGES
    # Pension alimentaires
    # Cotisations ou primes versées au titre de l'épargne retraite

    charges = cd_penali + cd_eparet

    return revenus - charges


def _bouclier_imp_gen (self, irpp, tax_hab_holder, tax_fonc, isf_tot, cotsoc_lib_holder, cotsoc_bar_holder,
        csgsald_holder, csgsali_holder, crdssal_holder, csgchoi_holder, csgchod_holder, csgrstd_holder,
        csgrsti_holder, imp_lib):  # # ajouter CSG- CRDS
    cotsoc_bar = self.sum_by_entity(cotsoc_bar_holder)
    cotsoc_lib = self.sum_by_entity(cotsoc_lib_holder)
    crdssal = self.sum_by_entity(crdssal_holder)
    csgchod = self.sum_by_entity(csgchod_holder)
    csgchoi = self.sum_by_entity(csgchoi_holder)
    csgsald = self.sum_by_entity(csgsald_holder)
    csgsali = self.sum_by_entity(csgsali_holder)
    csgrstd = self.sum_by_entity(csgrstd_holder)
    csgrsti = self.sum_by_entity(csgrsti_holder)
    tax_hab = self.cast_from_entity_to_role(tax_hab_holder, role = PREF)
    tax_hab = self.sum_by_entity(tax_hab)

    # # ajouter Prelèvements sources/ libé
    # # ajouter crds rstd
    # # impôt sur les plus-values immo et cession de fonds de commerce
    imp1 = cotsoc_lib + cotsoc_bar + csgsald + csgchod + crdssal + csgrstd + imp_lib
    '''
    Impôts payés en l'année 'n' au titre des revenus réalisés sur l'année 'n'
    '''
    imp2 = irpp + isf_tot + tax_hab + tax_fonc + csgsali + csgchoi + csgrsti
    '''
    Impôts payés en l'année 'n' au titre des revenus réalisés en 'n-1'
    '''
    return imp1 + imp2


def _restitutions(ppe, restit_imp):
    '''
    Restitutions d'impôt sur le revenu et degrèvements percus en l'année 'n'
    '''
    return ppe + restit_imp


def _bouclier_sumimp(bouclier_imp_gen, restitutions):
    '''
    Somme totale des impôts moins restitutions et degrèvements
    '''
    return -bouclier_imp_gen + restitutions


def _bouclier_fiscal(bouclier_sumimp, bouclier_rev, P = law.bouclier_fiscal):
    return max_(0, bouclier_sumimp - (bouclier_rev * P.taux))
