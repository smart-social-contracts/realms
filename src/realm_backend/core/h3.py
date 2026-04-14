"""
Pure-Python H3 geospatial indexing.

Faithful translation of Uber's H3 C reference implementation,
covering the functions needed by the realm backend:

  - geo_to_h3(lat, lng, resolution) -> str
  - h3_to_geo_boundary(h3_index) -> list[(lat, lng)]

Reference: https://h3geo.org  (Apache 2.0 license)
GitHub issue: https://github.com/smart-social-contracts/realms/issues/167
"""

import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EPSILON = 1e-14
_M_AP7_ROT_RADS = 0.3334731722518321153360907553516
_M_SQRT7 = 2.6457513110645905905016157536393
_M_RSQRT7 = 0.3779644730092272272145165362342
_M_SQRT3_2 = 0.8660254037844386467637231707529
_M_SIN60 = 0.8660254037844386467637231707529
_M_RSIN60 = 1.1547005383792515290182975610039
_RES0_U_GNOMONIC = 0.38196601125010500003
_INV_RES0_U_GNOMONIC = 2.61803398874989588842
_M_2PI = 2.0 * math.pi
_M_ONETHIRD = 1.0 / 3.0
_M_ONESEVENTH = 0.14285714285714285714285714285714285
_NUM_ICOSA_FACES = 20
_NUM_BASE_CELLS = 122
_MAX_H3_RES = 15
_NUM_HEX_VERTS = 6

# H3 index bit layout
_H3_MODE_OFFSET = 59
_H3_RES_OFFSET = 52
_H3_BC_OFFSET = 45
_H3_DIGIT_OFFSET = 42  # first digit starts at bit 42, each is 3 bits
_H3_CELL_MODE = 1
_H3_INIT = 0x08001fffffffffff  # mode=1, res=0, base=0, digits=all 7

# Direction digits
_CENTER_DIGIT = 0
_K_AXES_DIGIT = 1
_J_AXES_DIGIT = 2
_JK_AXES_DIGIT = 3
_I_AXES_DIGIT = 4
_IK_AXES_DIGIT = 5
_IJ_AXES_DIGIT = 6
_INVALID_DIGIT = 7

_UNIT_VECS = [
    (0, 0, 0),  # 0 center
    (0, 0, 1),  # 1 k
    (0, 1, 0),  # 2 j
    (0, 1, 1),  # 3 jk
    (1, 0, 0),  # 4 i
    (1, 0, 1),  # 5 ik
    (1, 1, 0),  # 6 ij
]

# ---------------------------------------------------------------------------
# Icosahedron face center points (unit sphere xyz)
# ---------------------------------------------------------------------------

_FACE_CENTER = [
    (0.2199307791404606, 0.6583691780274996, 0.7198475378926182),
    (-0.2139234834501421, 0.1478171829550703, 0.9656017935214205),
    (0.1092625278784797, -0.4811951572873210, 0.8697775121287253),
    (0.7428567301586791, -0.3593941678278028, 0.5648005936517033),
    (0.8112534709140969, 0.3448953237639384, 0.4721387736413930),
    (-0.1055498149613921, 0.9794457296411413, 0.1718874610009365),
    (-0.8075407579970092, 0.1533552485898818, 0.5695261994882688),
    (-0.2846148069787907, -0.8644080972654206, 0.4144792552473539),
    (0.7405621473854482, -0.6673299564565524, -0.0789837646326737),
    (0.8512303986474293, 0.4722343788582681, -0.2289137388687808),
    (-0.7405621473854481, 0.6673299564565524, 0.0789837646326737),
    (-0.8512303986474292, -0.4722343788582682, 0.2289137388687808),
    (0.1055498149613919, -0.9794457296411413, -0.1718874610009365),
    (0.8075407579970092, -0.1533552485898819, -0.5695261994882688),
    (0.2846148069787908, 0.8644080972654204, -0.4144792552473539),
    (-0.7428567301586791, 0.3593941678278027, -0.5648005936517033),
    (-0.8112534709140971, -0.3448953237639382, -0.4721387736413930),
    (-0.2199307791404607, -0.6583691780274996, -0.7198475378926182),
    (0.2139234834501420, -0.1478171829550704, -0.9656017935214205),
    (-0.1092625278784796, 0.4811951572873210, -0.8697775121287253),
]

# Face i-axis azimuth (first of three axes, Class II)
_FACE_AXES_AZ_CII_0 = [
    5.619958268523939882, 5.760339081714187279, 0.780213654393430055,
    0.430469363979999913, 6.130269123335111400, 2.692877706530642877,
    2.982963003477243874, 3.532912002790141181, 3.494305004259568154,
    3.003214169499538391, 5.930472956509811562, 0.138378484090254847,
    0.448714947059150361, 0.158629650112549365, 5.891865957979238535,
    2.711123289609793325, 3.294508837434268316, 3.804819692245439833,
    3.664438879055192436, 2.361378999196363184,
]

# ---------------------------------------------------------------------------
# Face neighbor orientation table
# faceNeighbors[face][dir] = (neighbor_face, translate_ijk, ccwRot60)
# dir: 0=center, 1=IJ, 2=KI, 3=JK
# ---------------------------------------------------------------------------

_IJ = 1
_KI = 2
_JK = 3

_FACE_NEIGHBORS = [
    [(0,(0,0,0),0),(4,(2,0,2),1),(1,(2,2,0),5),(5,(0,2,2),3)],
    [(1,(0,0,0),0),(0,(2,0,2),1),(2,(2,2,0),5),(6,(0,2,2),3)],
    [(2,(0,0,0),0),(1,(2,0,2),1),(3,(2,2,0),5),(7,(0,2,2),3)],
    [(3,(0,0,0),0),(2,(2,0,2),1),(4,(2,2,0),5),(8,(0,2,2),3)],
    [(4,(0,0,0),0),(3,(2,0,2),1),(0,(2,2,0),5),(9,(0,2,2),3)],
    [(5,(0,0,0),0),(10,(2,2,0),3),(14,(2,0,2),3),(0,(0,2,2),3)],
    [(6,(0,0,0),0),(11,(2,2,0),3),(10,(2,0,2),3),(1,(0,2,2),3)],
    [(7,(0,0,0),0),(12,(2,2,0),3),(11,(2,0,2),3),(2,(0,2,2),3)],
    [(8,(0,0,0),0),(13,(2,2,0),3),(12,(2,0,2),3),(3,(0,2,2),3)],
    [(9,(0,0,0),0),(14,(2,2,0),3),(13,(2,0,2),3),(4,(0,2,2),3)],
    [(10,(0,0,0),0),(5,(2,2,0),3),(6,(2,0,2),3),(15,(0,2,2),3)],
    [(11,(0,0,0),0),(6,(2,2,0),3),(7,(2,0,2),3),(16,(0,2,2),3)],
    [(12,(0,0,0),0),(7,(2,2,0),3),(8,(2,0,2),3),(17,(0,2,2),3)],
    [(13,(0,0,0),0),(8,(2,2,0),3),(9,(2,0,2),3),(18,(0,2,2),3)],
    [(14,(0,0,0),0),(9,(2,2,0),3),(5,(2,0,2),3),(19,(0,2,2),3)],
    [(15,(0,0,0),0),(16,(2,0,2),1),(19,(2,2,0),5),(10,(0,2,2),3)],
    [(16,(0,0,0),0),(17,(2,0,2),1),(15,(2,2,0),5),(11,(0,2,2),3)],
    [(17,(0,0,0),0),(18,(2,0,2),1),(16,(2,2,0),5),(12,(0,2,2),3)],
    [(18,(0,0,0),0),(19,(2,0,2),1),(17,(2,2,0),5),(13,(0,2,2),3)],
    [(19,(0,0,0),0),(15,(2,0,2),1),(18,(2,2,0),5),(14,(0,2,2),3)],
]

_ADJ_FACE_DIR = [
    [0,_KI,-1,-1,_IJ,_JK,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],
    [_IJ,0,_KI,-1,-1,-1,_JK,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],
    [-1,_IJ,0,_KI,-1,-1,-1,_JK,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],
    [-1,-1,_IJ,0,_KI,-1,-1,-1,_JK,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],
    [_KI,-1,-1,_IJ,0,-1,-1,-1,-1,_JK,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1],
    [_JK,-1,-1,-1,-1,0,-1,-1,-1,-1,_IJ,-1,-1,-1,_KI,-1,-1,-1,-1,-1],
    [-1,_JK,-1,-1,-1,-1,0,-1,-1,-1,_KI,_IJ,-1,-1,-1,-1,-1,-1,-1,-1],
    [-1,-1,_JK,-1,-1,-1,-1,0,-1,-1,-1,_KI,_IJ,-1,-1,-1,-1,-1,-1,-1],
    [-1,-1,-1,_JK,-1,-1,-1,-1,0,-1,-1,-1,_KI,_IJ,-1,-1,-1,-1,-1,-1],
    [-1,-1,-1,-1,_JK,-1,-1,-1,-1,0,-1,-1,-1,_KI,_IJ,-1,-1,-1,-1,-1],
    [-1,-1,-1,-1,-1,_IJ,_KI,-1,-1,-1,0,-1,-1,-1,-1,_JK,-1,-1,-1,-1],
    [-1,-1,-1,-1,-1,-1,_IJ,_KI,-1,-1,-1,0,-1,-1,-1,-1,_JK,-1,-1,-1],
    [-1,-1,-1,-1,-1,-1,-1,_IJ,_KI,-1,-1,-1,0,-1,-1,-1,-1,_JK,-1,-1],
    [-1,-1,-1,-1,-1,-1,-1,-1,_IJ,_KI,-1,-1,-1,0,-1,-1,-1,-1,_JK,-1],
    [-1,-1,-1,-1,-1,_KI,-1,-1,-1,_IJ,-1,-1,-1,-1,0,-1,-1,-1,-1,_JK],
    [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,_JK,-1,-1,-1,-1,0,_IJ,-1,-1,_KI],
    [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,_JK,-1,-1,-1,_KI,0,_IJ,-1,-1],
    [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,_JK,-1,-1,-1,_KI,0,_IJ,-1],
    [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,_JK,-1,-1,-1,_KI,0,_IJ],
    [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,_JK,_IJ,-1,-1,_KI,0],
]

# Overage distance table (Class II resolutions only: 0,2,4,...,16)
_MAX_DIM_BY_CII_RES = [2,-1,14,-1,98,-1,686,-1,4802,-1,33614,-1,235298,-1,1647086,-1,11529602]
_UNIT_SCALE_BY_CII_RES = [1,-1,7,-1,49,-1,343,-1,2401,-1,16807,-1,117649,-1,823543,-1,5764801]

# ---------------------------------------------------------------------------
# Base cell lookup table  faceIjkBaseCells[face][i][j][k] = (baseCell, ccwRot60)
# ---------------------------------------------------------------------------

_FIJKBC = [
 [  # face 0
  [[(16,0),(18,0),(24,0)],[(33,0),(30,0),(32,3)],[(49,1),(48,3),(50,3)]],
  [[(8,0),(5,5),(10,5)],[(22,0),(16,0),(18,0)],[(41,1),(33,0),(30,0)]],
  [[(4,0),(0,5),(2,5)],[(15,1),(8,0),(5,5)],[(31,1),(22,0),(16,0)]],
 ],
 [  # face 1
  [[(2,0),(6,0),(14,0)],[(10,0),(11,0),(17,3)],[(24,1),(23,3),(25,3)]],
  [[(0,0),(1,5),(9,5)],[(5,0),(2,0),(6,0)],[(18,1),(10,0),(11,0)]],
  [[(4,1),(3,5),(7,5)],[(8,1),(0,0),(1,5)],[(16,1),(5,0),(2,0)]],
 ],
 [  # face 2
  [[(7,0),(21,0),(38,0)],[(9,0),(19,0),(34,3)],[(14,1),(20,3),(36,3)]],
  [[(3,0),(13,5),(29,5)],[(1,0),(7,0),(21,0)],[(6,1),(9,0),(19,0)]],
  [[(4,2),(12,5),(26,5)],[(0,1),(3,0),(13,5)],[(2,1),(1,0),(7,0)]],
 ],
 [  # face 3
  [[(26,0),(42,0),(58,0)],[(29,0),(43,0),(62,3)],[(38,1),(47,3),(64,3)]],
  [[(12,0),(28,5),(44,5)],[(13,0),(26,0),(42,0)],[(21,1),(29,0),(43,0)]],
  [[(4,3),(15,5),(31,5)],[(3,1),(12,0),(28,5)],[(7,1),(13,0),(26,0)]],
 ],
 [  # face 4
  [[(31,0),(41,0),(49,0)],[(44,0),(53,0),(61,3)],[(58,1),(65,3),(75,3)]],
  [[(15,0),(22,5),(33,5)],[(28,0),(31,0),(41,0)],[(42,1),(44,0),(53,0)]],
  [[(4,4),(8,5),(16,5)],[(12,1),(15,0),(22,5)],[(26,1),(28,0),(31,0)]],
 ],
 [  # face 5
  [[(50,0),(48,0),(49,3)],[(32,0),(30,3),(33,3)],[(24,3),(18,3),(16,3)]],
  [[(70,0),(67,0),(66,3)],[(52,3),(50,0),(48,0)],[(37,3),(32,0),(30,3)]],
  [[(83,0),(87,3),(85,3)],[(74,3),(70,0),(67,0)],[(57,1),(52,3),(50,0)]],
 ],
 [  # face 6
  [[(25,0),(23,0),(24,3)],[(17,0),(11,3),(10,3)],[(14,3),(6,3),(2,3)]],
  [[(45,0),(39,0),(37,3)],[(35,3),(25,0),(23,0)],[(27,3),(17,0),(11,3)]],
  [[(63,0),(59,3),(57,3)],[(56,3),(45,0),(39,0)],[(46,3),(35,3),(25,0)]],
 ],
 [  # face 7
  [[(36,0),(20,0),(14,3)],[(34,0),(19,3),(9,3)],[(38,3),(21,3),(7,3)]],
  [[(55,0),(40,0),(27,3)],[(54,3),(36,0),(20,0)],[(51,3),(34,0),(19,3)]],
  [[(72,0),(60,3),(46,3)],[(73,3),(55,0),(40,0)],[(71,3),(54,3),(36,0)]],
 ],
 [  # face 8
  [[(64,0),(47,0),(38,3)],[(62,0),(43,3),(29,3)],[(58,3),(42,3),(26,3)]],
  [[(84,0),(69,0),(51,3)],[(82,3),(64,0),(47,0)],[(76,3),(62,0),(43,3)]],
  [[(97,0),(89,3),(71,3)],[(98,3),(84,0),(69,0)],[(96,3),(82,3),(64,0)]],
 ],
 [  # face 9
  [[(75,0),(65,0),(58,3)],[(61,0),(53,3),(44,3)],[(49,3),(41,3),(31,3)]],
  [[(94,0),(86,0),(76,3)],[(81,3),(75,0),(65,0)],[(66,3),(61,0),(53,3)]],
  [[(107,0),(104,3),(96,3)],[(101,3),(94,0),(86,0)],[(85,3),(81,3),(75,0)]],
 ],
 [  # face 10
  [[(57,0),(59,0),(63,3)],[(74,0),(78,3),(79,3)],[(83,3),(92,3),(95,3)]],
  [[(37,0),(39,3),(45,3)],[(52,0),(57,0),(59,0)],[(70,3),(74,0),(78,3)]],
  [[(24,0),(23,3),(25,3)],[(32,3),(37,0),(39,3)],[(50,3),(52,0),(57,0)]],
 ],
 [  # face 11
  [[(46,0),(60,0),(72,3)],[(56,0),(68,3),(80,3)],[(63,3),(77,3),(90,3)]],
  [[(27,0),(40,3),(55,3)],[(35,0),(46,0),(60,0)],[(45,3),(56,0),(68,3)]],
  [[(14,0),(20,3),(36,3)],[(17,3),(27,0),(40,3)],[(25,3),(35,0),(46,0)]],
 ],
 [  # face 12
  [[(71,0),(89,0),(97,3)],[(73,0),(91,3),(103,3)],[(72,3),(88,3),(105,3)]],
  [[(51,0),(69,3),(84,3)],[(54,0),(71,0),(89,0)],[(55,3),(73,0),(91,3)]],
  [[(38,0),(47,3),(64,3)],[(34,3),(51,0),(69,3)],[(36,3),(54,0),(71,0)]],
 ],
 [  # face 13
  [[(96,0),(104,0),(107,3)],[(98,0),(110,3),(115,3)],[(97,3),(111,3),(119,3)]],
  [[(76,0),(86,3),(94,3)],[(82,0),(96,0),(104,0)],[(84,3),(98,0),(110,3)]],
  [[(58,0),(65,3),(75,3)],[(62,3),(76,0),(86,3)],[(64,3),(82,0),(96,0)]],
 ],
 [  # face 14
  [[(85,0),(87,0),(83,3)],[(101,0),(102,3),(100,3)],[(107,3),(112,3),(114,3)]],
  [[(66,0),(67,3),(70,3)],[(81,0),(85,0),(87,0)],[(94,3),(101,0),(102,3)]],
  [[(49,0),(48,3),(50,3)],[(61,3),(66,0),(67,3)],[(75,3),(81,0),(85,0)]],
 ],
 [  # face 15
  [[(95,0),(92,0),(83,0)],[(79,0),(78,0),(74,3)],[(63,1),(59,3),(57,3)]],
  [[(109,0),(108,0),(100,5)],[(93,1),(95,0),(92,0)],[(77,1),(79,0),(78,0)]],
  [[(117,4),(118,5),(114,5)],[(106,1),(109,0),(108,0)],[(90,1),(93,1),(95,0)]],
 ],
 [  # face 16
  [[(90,0),(77,0),(63,0)],[(80,0),(68,0),(56,3)],[(72,1),(60,3),(46,3)]],
  [[(106,0),(93,0),(79,5)],[(99,1),(90,0),(77,0)],[(88,1),(80,0),(68,0)]],
  [[(117,3),(109,5),(95,5)],[(113,1),(106,0),(93,0)],[(105,1),(99,1),(90,0)]],
 ],
 [  # face 17
  [[(105,0),(88,0),(72,0)],[(103,0),(91,0),(73,3)],[(97,1),(89,3),(71,3)]],
  [[(113,0),(99,0),(80,5)],[(116,1),(105,0),(88,0)],[(111,1),(103,0),(91,0)]],
  [[(117,2),(106,5),(90,5)],[(121,1),(113,0),(99,0)],[(119,1),(116,1),(105,0)]],
 ],
 [  # face 18
  [[(119,0),(111,0),(97,0)],[(115,0),(110,0),(98,3)],[(107,1),(104,3),(96,3)]],
  [[(121,0),(116,0),(103,5)],[(120,1),(119,0),(111,0)],[(112,1),(115,0),(110,0)]],
  [[(117,1),(113,5),(105,5)],[(118,1),(121,0),(116,0)],[(114,1),(120,1),(119,0)]],
 ],
 [  # face 19
  [[(114,0),(112,0),(107,0)],[(100,0),(102,0),(101,3)],[(83,1),(87,3),(85,3)]],
  [[(118,0),(120,0),(115,5)],[(108,1),(114,0),(112,0)],[(92,1),(100,0),(102,0)]],
  [[(117,0),(121,5),(119,5)],[(109,1),(118,0),(120,0)],[(95,1),(108,1),(114,0)]],
 ],
]

# Base cell data: (home_face, home_i, home_j, home_k, is_pentagon, cwOffset0, cwOffset1)
_BASE_CELL_DATA = [
    (1,1,0,0,0,-1,-1),(2,1,1,0,0,-1,-1),(1,0,0,0,0,-1,-1),(2,1,0,0,0,-1,-1),
    (0,2,0,0,1,-1,-1),(1,1,1,0,0,-1,-1),(1,0,0,1,0,-1,-1),(2,0,0,0,0,-1,-1),
    (0,1,0,0,0,-1,-1),(2,0,1,0,0,-1,-1),(1,0,1,0,0,-1,-1),(1,0,1,1,0,-1,-1),
    (3,1,0,0,0,-1,-1),(3,1,1,0,0,-1,-1),(11,2,0,0,1,2,6),(4,1,0,0,0,-1,-1),
    (0,0,0,0,0,-1,-1),(6,0,1,0,0,-1,-1),(0,0,0,1,0,-1,-1),(2,0,1,1,0,-1,-1),
    (7,0,0,1,0,-1,-1),(2,0,0,1,0,-1,-1),(0,1,1,0,0,-1,-1),(6,0,0,1,0,-1,-1),
    (10,2,0,0,1,1,5),(6,0,0,0,0,-1,-1),(3,0,0,0,0,-1,-1),(11,1,0,0,0,-1,-1),
    (4,1,1,0,0,-1,-1),(3,0,1,0,0,-1,-1),(0,0,1,1,0,-1,-1),(4,0,0,0,0,-1,-1),
    (5,0,1,0,0,-1,-1),(0,0,1,0,0,-1,-1),(7,0,1,0,0,-1,-1),(11,1,1,0,0,-1,-1),
    (7,0,0,0,0,-1,-1),(10,1,0,0,0,-1,-1),(12,2,0,0,1,3,7),(6,1,0,1,0,-1,-1),
    (7,1,0,1,0,-1,-1),(4,0,0,1,0,-1,-1),(3,0,0,1,0,-1,-1),(3,0,1,1,0,-1,-1),
    (4,0,1,0,0,-1,-1),(6,1,0,0,0,-1,-1),(11,0,0,0,0,-1,-1),(8,0,0,1,0,-1,-1),
    (5,0,0,1,0,-1,-1),(14,2,0,0,1,0,9),(5,0,0,0,0,-1,-1),(12,1,0,0,0,-1,-1),
    (10,1,1,0,0,-1,-1),(4,0,1,1,0,-1,-1),(12,1,1,0,0,-1,-1),(7,1,0,0,0,-1,-1),
    (11,0,1,0,0,-1,-1),(10,0,0,0,0,-1,-1),(13,2,0,0,1,4,8),(10,0,0,1,0,-1,-1),
    (11,0,0,1,0,-1,-1),(9,0,1,0,0,-1,-1),(8,0,1,0,0,-1,-1),(6,2,0,0,1,11,15),
    (8,0,0,0,0,-1,-1),(9,0,0,1,0,-1,-1),(14,1,0,0,0,-1,-1),(5,1,0,1,0,-1,-1),
    (16,0,1,1,0,-1,-1),(8,1,0,1,0,-1,-1),(5,1,0,0,0,-1,-1),(12,0,0,0,0,-1,-1),
    (7,2,0,0,1,12,16),(12,0,1,0,0,-1,-1),(10,0,1,0,0,-1,-1),(9,0,0,0,0,-1,-1),
    (13,1,0,0,0,-1,-1),(16,0,0,1,0,-1,-1),(15,0,1,1,0,-1,-1),(15,0,1,0,0,-1,-1),
    (16,0,1,0,0,-1,-1),(14,1,1,0,0,-1,-1),(13,1,1,0,0,-1,-1),(5,2,0,0,1,10,19),
    (8,1,0,0,0,-1,-1),(14,0,0,0,0,-1,-1),(9,1,0,1,0,-1,-1),(14,0,0,1,0,-1,-1),
    (17,0,0,1,0,-1,-1),(12,0,0,1,0,-1,-1),(16,0,0,0,0,-1,-1),(17,0,1,1,0,-1,-1),
    (15,0,0,1,0,-1,-1),(16,1,0,1,0,-1,-1),(9,1,0,0,0,-1,-1),(15,0,0,0,0,-1,-1),
    (13,0,0,0,0,-1,-1),(8,2,0,0,1,13,17),(13,0,1,0,0,-1,-1),(17,1,0,1,0,-1,-1),
    (19,0,1,0,0,-1,-1),(14,0,1,0,0,-1,-1),(19,0,1,1,0,-1,-1),(17,0,1,0,0,-1,-1),
    (13,0,0,1,0,-1,-1),(17,0,0,0,0,-1,-1),(16,1,0,0,0,-1,-1),(9,2,0,0,1,14,18),
    (15,1,0,1,0,-1,-1),(15,1,0,0,0,-1,-1),(18,0,1,1,0,-1,-1),(18,0,0,1,0,-1,-1),
    (19,0,0,1,0,-1,-1),(17,1,0,0,0,-1,-1),(19,0,0,0,0,-1,-1),(18,0,1,0,0,-1,-1),
    (18,1,0,1,0,-1,-1),(19,2,0,0,1,-1,-1),(19,1,0,0,0,-1,-1),(18,0,0,0,0,-1,-1),
    (19,1,0,1,0,-1,-1),(18,1,0,0,0,-1,-1),
]

# ---------------------------------------------------------------------------
# Vec3d helpers
# ---------------------------------------------------------------------------

def _v3_dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def _v3_cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def _v3_scale(a, s):
    return (a[0]*s, a[1]*s, a[2]*s)

def _v3_add(a, b):
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])

def _v3_sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def _v3_norm(a):
    m = math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])
    if m < _EPSILON:
        return a
    return (a[0]/m, a[1]/m, a[2]/m)

def _v3_dist_sq(a, b):
    d = _v3_sub(a, b)
    return d[0]*d[0]+d[1]*d[1]+d[2]*d[2]

def _v3_lincomb(s1, a, s2, b):
    return (s1*a[0]+s2*b[0], s1*a[1]+s2*b[1], s1*a[2]+s2*b[2])

# ---------------------------------------------------------------------------
# IJK coordinate operations
# ---------------------------------------------------------------------------

def _ijk_normalize(i, j, k):
    if i < 0:
        j -= i; k -= i; i = 0
    if j < 0:
        i -= j; k -= j; j = 0
    if k < 0:
        i -= k; j -= k; k = 0
    m = min(i, j, k)
    return (i - m, j - m, k - m)

def _ijk_add(a, b):
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])

def _ijk_sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def _ijk_scale(ijk, s):
    return (ijk[0]*s, ijk[1]*s, ijk[2]*s)

def _lround(x):
    """Round to nearest integer, halfway away from zero (matches C lroundl)."""
    if x >= 0:
        return int(math.floor(x + 0.5))
    else:
        return int(math.ceil(x - 0.5))

def _up_ap7(i, j, k):
    ci = i - k
    cj = j - k
    ni = _lround((3 * ci - cj) * _M_ONESEVENTH)
    nj = _lround((ci + 2 * cj) * _M_ONESEVENTH)
    return _ijk_normalize(ni, nj, 0)

def _up_ap7r(i, j, k):
    ci = i - k
    cj = j - k
    ni = _lround((2 * ci + cj) * _M_ONESEVENTH)
    nj = _lround((3 * cj - ci) * _M_ONESEVENTH)
    return _ijk_normalize(ni, nj, 0)

def _down_ap7(i, j, k):
    iv = _ijk_scale((3, 0, 1), i)
    jv = _ijk_scale((1, 3, 0), j)
    kv = _ijk_scale((0, 1, 3), k)
    s = _ijk_add(_ijk_add(iv, jv), kv)
    return _ijk_normalize(*s)

def _down_ap7r(i, j, k):
    iv = _ijk_scale((3, 1, 0), i)
    jv = _ijk_scale((0, 3, 1), j)
    kv = _ijk_scale((1, 0, 3), k)
    s = _ijk_add(_ijk_add(iv, jv), kv)
    return _ijk_normalize(*s)

def _down_ap3(i, j, k):
    iv = _ijk_scale((2, 0, 1), i)
    jv = _ijk_scale((1, 2, 0), j)
    kv = _ijk_scale((0, 1, 2), k)
    s = _ijk_add(_ijk_add(iv, jv), kv)
    return _ijk_normalize(*s)

def _down_ap3r(i, j, k):
    iv = _ijk_scale((2, 1, 0), i)
    jv = _ijk_scale((0, 2, 1), j)
    kv = _ijk_scale((1, 0, 2), k)
    s = _ijk_add(_ijk_add(iv, jv), kv)
    return _ijk_normalize(*s)

def _ijk_rotate60ccw(i, j, k):
    iv = _ijk_scale((1, 1, 0), i)
    jv = _ijk_scale((0, 1, 1), j)
    kv = _ijk_scale((1, 0, 1), k)
    s = _ijk_add(_ijk_add(iv, jv), kv)
    return _ijk_normalize(*s)

def _ijk_rotate60cw(i, j, k):
    iv = _ijk_scale((1, 0, 1), i)
    jv = _ijk_scale((1, 1, 0), j)
    kv = _ijk_scale((0, 1, 1), k)
    s = _ijk_add(_ijk_add(iv, jv), kv)
    return _ijk_normalize(*s)

def _unit_ijk_to_digit(i, j, k):
    i, j, k = _ijk_normalize(i, j, k)
    for d in range(7):
        if (i, j, k) == _UNIT_VECS[d]:
            return d
    return _INVALID_DIGIT

def _rotate60ccw_digit(d):
    return [0, 5, 3, 1, 6, 4, 2, 7][d] if 0 <= d <= 7 else d

def _rotate60cw_digit(d):
    return [0, 3, 6, 2, 5, 1, 4, 7][d] if 0 <= d <= 7 else d

# ---------------------------------------------------------------------------
# hex2d <-> IJK
# ---------------------------------------------------------------------------

def _hex2d_to_coord_ijk(x, y):
    k = 0
    a1 = abs(x)
    a2 = abs(y)
    x2 = a2 * _M_RSIN60
    x1 = a1 + x2 / 2.0
    m1 = int(x1)
    m2 = int(x2)
    r1 = x1 - m1
    r2 = x2 - m2

    if r1 < 0.5:
        if r1 < 1.0 / 3.0:
            if r2 < (1.0 + r1) / 2.0:
                i, j = m1, m2
            else:
                i, j = m1, m2 + 1
        else:
            if r2 < (1.0 - r1):
                j = m2
            else:
                j = m2 + 1
            if (1.0 - r1) <= r2 and r2 < (2.0 * r1):
                i = m1 + 1
            else:
                i = m1
    else:
        if r1 < 2.0 / 3.0:
            if r2 < (1.0 - r1):
                j = m2
            else:
                j = m2 + 1
            if (2.0 * r1 - 1.0) < r2 and r2 < (1.0 - r1):
                i = m1
            else:
                i = m1 + 1
        else:
            if r2 < (r1 / 2.0):
                i, j = m1 + 1, m2
            else:
                i, j = m1 + 1, m2 + 1

    if x < 0.0:
        if (j % 2) == 0:
            axisi = j // 2
            diff = i - axisi
            i = int(i - 2 * diff)
        else:
            axisi = (j + 1) // 2
            diff = i - axisi
            i = int(i - (2 * diff + 1))

    if y < 0.0:
        i = i - (2 * j + 1) // 2
        j = -j

    return _ijk_normalize(i, j, k)

def _ijk_to_hex2d(i, j, k):
    ci = i - k
    cj = j - k
    x = ci - 0.5 * cj
    y = cj * _M_SQRT3_2
    return (x, y)

# ---------------------------------------------------------------------------
# Geo <-> Vec3d
# ---------------------------------------------------------------------------

def _geo_to_vec3d(lat_deg, lng_deg):
    lat = math.radians(lat_deg)
    lng = math.radians(lng_deg)
    cl = math.cos(lat)
    return (cl * math.cos(lng), cl * math.sin(lng), math.sin(lat))

def _vec3d_to_geo(v):
    lat = math.asin(max(-1.0, min(1.0, v[2])))
    lng = math.atan2(v[1], v[0])
    return (math.degrees(lat), math.degrees(lng))

# ---------------------------------------------------------------------------
# Core projection: Vec3d -> FaceIJK
# ---------------------------------------------------------------------------

def _pos_angle(rads):
    tmp = rads % _M_2PI
    if tmp < 0.0:
        tmp += _M_2PI
    return tmp

def _vec3_to_closest_face(p):
    best_face = 0
    best_sqd = 5.0
    for f in range(_NUM_ICOSA_FACES):
        sqd = _v3_dist_sq(_FACE_CENTER[f], p)
        if sqd < best_sqd:
            best_face = f
            best_sqd = sqd
    return best_face, best_sqd

def _vec3_tangent_basis(p):
    north_pole = (0.0, 0.0, 1.0)
    north = _v3_lincomb(1.0, north_pole, -_v3_dot(north_pole, p), p)
    north = _v3_norm(north)
    east = _v3_cross(north, p)
    return north, east

def _vec3_azimuth_rads(p1, p2):
    north, east = _vec3_tangent_basis(p1)
    p2proj = _v3_lincomb(1.0, p2, -_v3_dot(p2, p1), p1)
    p2proj = _v3_norm(p2proj)
    return math.atan2(_v3_dot(p2proj, east), _v3_dot(p2proj, north))

def _vec3_to_hex2d_on_face(p, face, res):
    sqd = _v3_dist_sq(_FACE_CENTER[face], p)
    r = math.acos(max(-1.0, min(1.0, 1.0 - sqd * 0.5)))
    if r < _EPSILON:
        return 0.0, 0.0

    theta = _pos_angle(
        _FACE_AXES_AZ_CII_0[face]
        - _pos_angle(_vec3_azimuth_rads(_FACE_CENTER[face], p))
    )

    if res % 2 == 1:  # Class III
        theta = _pos_angle(theta - _M_AP7_ROT_RADS)

    r = math.tan(r)
    r *= _INV_RES0_U_GNOMONIC
    for _ in range(res):
        r *= _M_SQRT7

    return r * math.cos(theta), r * math.sin(theta)

def _vec3_to_hex2d(p, res):
    face, _ = _vec3_to_closest_face(p)
    hx, hy = _vec3_to_hex2d_on_face(p, face, res)
    return face, hx, hy

def _walk_up_to_res0(ijk, res):
    """Walk IJK at target res up to resolution 0, return res-0 IJK."""
    i, j, k = ijk
    for r in range(res - 1, -1, -1):
        if (r + 1) % 2 == 1:
            i, j, k = _up_ap7(i, j, k)
        else:
            i, j, k = _up_ap7r(i, j, k)
    return (i, j, k)

def _vec3_to_face_ijk(p, res):
    face, hx, hy = _vec3_to_hex2d(p, res)
    ijk = _hex2d_to_coord_ijk(hx, hy)

    if res == 0:
        return face, ijk

    r0 = _walk_up_to_res0(ijk, res)
    if max(r0) > 2:
        # Out of face bounds; try adjacent faces
        candidates = []
        for f in range(_NUM_ICOSA_FACES):
            if f == face:
                continue
            dot = _v3_dot(_FACE_CENTER[f], p)
            candidates.append((dot, f))
        candidates.sort(reverse=True)
        for _, alt_face in candidates[:3]:
            alt_hx, alt_hy = _vec3_to_hex2d_on_face(p, alt_face, res)
            alt_ijk = _hex2d_to_coord_ijk(alt_hx, alt_hy)
            alt_r0 = _walk_up_to_res0(alt_ijk, res)
            if max(alt_r0) <= 2:
                return alt_face, alt_ijk

    return face, ijk

# ---------------------------------------------------------------------------
# FaceIJK -> H3 index
# ---------------------------------------------------------------------------

def _is_base_cell_pentagon(bc):
    return _BASE_CELL_DATA[bc][4] == 1

def _base_cell_is_cw_offset(bc, test_face):
    d = _BASE_CELL_DATA[bc]
    return d[5] == test_face or d[6] == test_face

def _h3_get_digit(h, r):
    return (h >> ((_MAX_H3_RES - r) * 3)) & 7

def _h3_set_digit(h, r, d):
    shift = (_MAX_H3_RES - r) * 3
    h &= ~(7 << shift)
    h |= (d & 7) << shift
    return h

def _h3_rotate60ccw(h, res):
    for r in range(1, res + 1):
        old = _h3_get_digit(h, r)
        h = _h3_set_digit(h, r, _rotate60ccw_digit(old))
    return h

def _h3_rotate60cw(h, res):
    for r in range(1, res + 1):
        old = _h3_get_digit(h, r)
        h = _h3_set_digit(h, r, _rotate60cw_digit(old))
    return h

def _h3_leading_nonzero_digit(h, res):
    for r in range(1, res + 1):
        d = _h3_get_digit(h, r)
        if d != _CENTER_DIGIT:
            return d
    return _CENTER_DIGIT

def _h3_rotate_pent60ccw(h, res):
    """Rotate an H3Index 60 degrees CCW about a pentagonal center.
    Handles the deleted k-axes subsequence inline during rotation."""
    found_first = False
    for r in range(1, res + 1):
        old = _h3_get_digit(h, r)
        h = _h3_set_digit(h, r, _rotate60ccw_digit(old))
        if not found_first and _h3_get_digit(h, r) != _CENTER_DIGIT:
            found_first = True
            if _h3_leading_nonzero_digit(h, res) == _K_AXES_DIGIT:
                h = _h3_rotate60ccw(h, res)
    return h

def _h3_rotate_pent60cw(h, res):
    """Rotate an H3Index 60 degrees CW about a pentagonal center.
    Handles the deleted k-axes subsequence inline during rotation."""
    found_first = False
    for r in range(1, res + 1):
        old = _h3_get_digit(h, r)
        h = _h3_set_digit(h, r, _rotate60cw_digit(old))
        if not found_first and _h3_get_digit(h, r) != _CENTER_DIGIT:
            found_first = True
            if _h3_leading_nonzero_digit(h, res) == _K_AXES_DIGIT:
                h = _h3_rotate60cw(h, res)
    return h

def _face_ijk_to_h3(face, ijk, res):
    h = _H3_INIT
    h = (h & ~(0xF << _H3_MODE_OFFSET)) | (_H3_CELL_MODE << _H3_MODE_OFFSET)
    h = (h & ~(0xF << _H3_RES_OFFSET)) | (res << _H3_RES_OFFSET)

    if res == 0:
        bc_entry = _FIJKBC[face][ijk[0]][ijk[1]][ijk[2]]
        bc = bc_entry[0]
        h = (h & ~(0x7F << _H3_BC_OFFSET)) | (bc << _H3_BC_OFFSET)
        return h

    i, j, k = ijk
    for r in range(res - 1, -1, -1):
        last_i, last_j, last_k = i, j, k
        if (r + 1) % 2 == 1:  # Class III
            i, j, k = _up_ap7(i, j, k)
            ci, cj, ck = _down_ap7(i, j, k)
        else:
            i, j, k = _up_ap7r(i, j, k)
            ci, cj, ck = _down_ap7r(i, j, k)

        diff = _ijk_sub((last_i, last_j, last_k), (ci, cj, ck))
        diff = _ijk_normalize(*diff)
        digit = _unit_ijk_to_digit(*diff)
        h = _h3_set_digit(h, r + 1, digit)

    if i > 2 or j > 2 or k > 2:
        return 0

    bc_entry = _FIJKBC[face][i][j][k]
    bc = bc_entry[0]
    num_rots = bc_entry[1]

    h = (h & ~(0x7F << _H3_BC_OFFSET)) | (bc << _H3_BC_OFFSET)

    if _is_base_cell_pentagon(bc):
        if _h3_leading_nonzero_digit(h, res) == _K_AXES_DIGIT:
            if _base_cell_is_cw_offset(bc, face):
                h = _h3_rotate60cw(h, res)
            else:
                h = _h3_rotate60ccw(h, res)
        for _ in range(num_rots):
            h = _h3_rotate_pent60ccw(h, res)
    else:
        for _ in range(num_rots):
            h = _h3_rotate60ccw(h, res)

    return h

# ---------------------------------------------------------------------------
# H3 index -> FaceIJK (decoding)
# ---------------------------------------------------------------------------

def _h3_to_face_ijk(h):
    res = (h >> _H3_RES_OFFSET) & 0xF
    bc = (h >> _H3_BC_OFFSET) & 0x7F
    d = _BASE_CELL_DATA[bc]
    face = d[0]
    ijk = [d[1], d[2], d[3]]

    if not _is_base_cell_pentagon(bc):
        num_rots = _FIJKBC[face][ijk[0]][ijk[1]][ijk[2]][1]
        for r in range(1, res + 1):
            if r % 2 == 1:  # Class III
                ijk[0], ijk[1], ijk[2] = _down_ap7(ijk[0], ijk[1], ijk[2])
            else:
                ijk[0], ijk[1], ijk[2] = _down_ap7r(ijk[0], ijk[1], ijk[2])
            digit = _h3_get_digit(h, r)
            digit_rotated = digit
            for _ in range(num_rots):
                digit_rotated = _rotate60ccw_digit(digit_rotated)
            if digit_rotated != _CENTER_DIGIT:
                uv = _UNIT_VECS[digit_rotated]
                ijk[0] += uv[0]
                ijk[1] += uv[1]
                ijk[2] += uv[2]
                ijk[0], ijk[1], ijk[2] = _ijk_normalize(ijk[0], ijk[1], ijk[2])
    else:
        num_rots = _FIJKBC[face][ijk[0]][ijk[1]][ijk[2]][1]
        for r in range(1, res + 1):
            if r % 2 == 1:
                ijk[0], ijk[1], ijk[2] = _down_ap7(ijk[0], ijk[1], ijk[2])
            else:
                ijk[0], ijk[1], ijk[2] = _down_ap7r(ijk[0], ijk[1], ijk[2])
            digit = _h3_get_digit(h, r)
            digit_rotated = digit
            for _ in range(num_rots):
                digit_rotated = _rotate60ccw_digit(digit_rotated)
            if digit_rotated == _K_AXES_DIGIT:
                digit_rotated = _IK_AXES_DIGIT
                num_rots += 1
            if digit_rotated != _CENTER_DIGIT:
                uv = _UNIT_VECS[digit_rotated]
                ijk[0] += uv[0]
                ijk[1] += uv[1]
                ijk[2] += uv[2]
                ijk[0], ijk[1], ijk[2] = _ijk_normalize(ijk[0], ijk[1], ijk[2])

    return face, tuple(ijk), res

# ---------------------------------------------------------------------------
# Boundary computation
# ---------------------------------------------------------------------------

def _hex2d_to_vec3(hx, hy, face, res, substrate):
    r = math.sqrt(hx * hx + hy * hy)
    if r < _EPSILON:
        return _FACE_CENTER[face]

    theta = math.atan2(hy, hx)
    for _ in range(res):
        r *= _M_RSQRT7
    if substrate:
        r *= _M_ONETHIRD
        if res % 2 == 1:
            r *= _M_RSQRT7
    r *= _RES0_U_GNOMONIC
    r = math.atan(r)

    if not substrate and res % 2 == 1:
        theta = _pos_angle(theta + _M_AP7_ROT_RADS)

    theta = _pos_angle(_FACE_AXES_AZ_CII_0[face] - theta)

    north, east = _vec3_tangent_basis(_FACE_CENTER[face])
    direction = _v3_lincomb(math.cos(theta), north, math.sin(theta), east)
    v3 = _v3_lincomb(math.cos(r), _FACE_CENTER[face], math.sin(r), direction)
    return _v3_norm(v3)

_NO_OVERAGE = 0
_FACE_EDGE = 1
_NEW_FACE = 2

def _adjust_overage_class_ii(face, i, j, k, res, pent_leading4, substrate):
    max_dim = _MAX_DIM_BY_CII_RES[res]
    if substrate:
        max_dim *= 3

    overage = _NO_OVERAGE
    if substrate and i + j + k == max_dim:
        overage = _FACE_EDGE
    elif i + j + k > max_dim:
        overage = _NEW_FACE
        if k > 0:
            if j > 0:
                d = _JK
            else:
                d = _KI
                if pent_leading4:
                    origin = (max_dim, 0, 0)
                    tmp = _ijk_sub((i, j, k), origin)
                    tmp = _ijk_rotate60cw(*tmp)
                    i, j, k = _ijk_add(tmp, origin)
        else:
            d = _IJ

        fn = _FACE_NEIGHBORS[face][d]
        face = fn[0]
        trans = fn[1]
        ccw_rot = fn[2]

        for _ in range(ccw_rot):
            i, j, k = _ijk_rotate60ccw(i, j, k)

        unit_scale = _UNIT_SCALE_BY_CII_RES[res]
        if substrate:
            unit_scale *= 3
        scaled_trans = _ijk_scale(trans, unit_scale)
        i, j, k = _ijk_normalize(*_ijk_add((i, j, k), scaled_trans))

        if substrate and i + j + k == max_dim:
            overage = _FACE_EDGE

    return face, i, j, k, overage

def _v2d_intersect(a0x, a0y, a1x, a1y, b0x, b0y, b1x, b1y):
    dax = a1x - a0x
    day = a1y - a0y
    dbx = b1x - b0x
    dby = b1y - b0y
    t = ((b0x - a0x) * dby - (b0y - a0y) * dbx) / (dax * dby - day * dbx + _EPSILON)
    return (a0x + t * dax, a0y + t * day)

def _face_ijk_to_cell_boundary(face, ijk, res):
    adj_res = res
    ci, cj, ck = ijk

    if res % 2 == 1:  # Class III
        verts_offsets = [(5,4,0),(1,5,0),(0,5,4),(0,1,5),(4,0,5),(5,0,1)]
    else:
        verts_offsets = [(2,1,0),(1,2,0),(0,2,1),(0,1,2),(1,0,2),(2,0,1)]

    ci, cj, ck = _down_ap3(ci, cj, ck)
    ci, cj, ck = _down_ap3r(ci, cj, ck)

    if res % 2 == 1:
        ci, cj, ck = _down_ap7r(ci, cj, ck)
        adj_res += 1

    fijk_verts = []
    for v in range(_NUM_HEX_VERTS):
        vi, vj, vk = verts_offsets[v]
        fi = ci + vi
        fj = cj + vj
        fk = ck + vk
        fi, fj, fk = _ijk_normalize(fi, fj, fk)
        fijk_verts.append((face, fi, fj, fk))

    boundary = []
    last_face = -1
    last_overage = _NO_OVERAGE

    for vert_idx in range(_NUM_HEX_VERTS + 1):
        v = vert_idx % _NUM_HEX_VERTS
        vf, vi, vj, vk = fijk_verts[v]

        adj_face, vi, vj, vk, overage = _adjust_overage_class_ii(
            vf, vi, vj, vk, adj_res, 0, 1
        )

        if (res % 2 == 1 and vert_idx > 0 and
                adj_face != last_face and last_overage != _FACE_EDGE):
            last_v = (v + 5) % _NUM_HEX_VERTS
            o0x, o0y = _ijk_to_hex2d(*fijk_verts[last_v][1:])
            o1x, o1y = _ijk_to_hex2d(*fijk_verts[v][1:])

            max_dim = _MAX_DIM_BY_CII_RES[adj_res]
            v0 = (3.0*max_dim, 0.0)
            v1 = (-1.5*max_dim, 3.0*_M_SQRT3_2*max_dim)
            v2 = (-1.5*max_dim, -3.0*_M_SQRT3_2*max_dim)

            face2 = last_face if last_face != face else adj_face
            d = _ADJ_FACE_DIR[face][face2]
            if d == _IJ:
                e0, e1 = v0, v1
            elif d == _JK:
                e0, e1 = v1, v2
            else:
                e0, e1 = v2, v0

            ix, iy = _v2d_intersect(o0x, o0y, o1x, o1y, e0[0], e0[1], e1[0], e1[1])

            almost0 = abs(o0x - ix) < _EPSILON and abs(o0y - iy) < _EPSILON
            almost1 = abs(o1x - ix) < _EPSILON and abs(o1y - iy) < _EPSILON
            if not almost0 and not almost1:
                pv = _hex2d_to_vec3(ix, iy, face, adj_res, 1)
                boundary.append(_vec3d_to_geo(pv))

        if vert_idx < _NUM_HEX_VERTS:
            hx, hy = _ijk_to_hex2d(vi, vj, vk)
            pv = _hex2d_to_vec3(hx, hy, adj_face, adj_res, 1)
            boundary.append(_vec3d_to_geo(pv))

        last_face = adj_face
        last_overage = overage

    return boundary

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def geo_to_h3(lat, lng, resolution):
    """Convert latitude/longitude to H3 cell index string.

    Args:
        lat: Latitude in degrees.
        lng: Longitude in degrees.
        resolution: H3 resolution (0-15).

    Returns:
        H3 cell index as a hex string (e.g. '872830828ffffff').
    """
    if resolution < 0 or resolution > _MAX_H3_RES:
        raise ValueError(f"Resolution must be 0-{_MAX_H3_RES}")
    p = _geo_to_vec3d(lat, lng)
    face, ijk = _vec3_to_face_ijk(p, resolution)
    h = _face_ijk_to_h3(face, ijk, resolution)
    return format(h, 'x')


def h3_to_geo_boundary(h3_index):
    """Get the boundary vertices of an H3 cell.

    Args:
        h3_index: H3 cell index as a hex string.

    Returns:
        List of (lat, lng) tuples forming the cell boundary.
    """
    h = int(h3_index, 16)
    face, ijk, res = _h3_to_face_ijk(h)
    return _face_ijk_to_cell_boundary(face, ijk, res)
