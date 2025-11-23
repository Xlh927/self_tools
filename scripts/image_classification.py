#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像分类模块（A5）

功能：
- 支持多种预训练模型加载与推理
- 自定义模型加载与分类
- 图像预处理
- 分类结果可视化与导出
- 支持单文件和批量文件夹处理
"""

import os
import cv2
import numpy as np
import argparse
import json
from tqdm import tqdm
from PIL import Image
import torch
import torchvision
from torchvision import transforms
import tensorflow as tf
from tensorflow.keras.applications import (ResNet50, VGG16, MobileNetV2,
                                         InceptionV3, Xception)
from tensorflow.keras.applications.imagenet_utils import decode_predictions

class ImageClassifier:
    """图像分类器类"""
    
    def __init__(self, model_type='resnet50', device='auto', custom_model_path=None):
        """
        初始化分类器
        
        Args:
            model_type: 模型类型，支持'resnet50', 'vgg16', 'mobilenetv2', 'inceptionv3', 'xception', 'custom'
            device: 运行设备，'auto', 'cuda', 'cpu'
            custom_model_path: 自定义模型路径
        """
        self.model_type = model_type
        self.model = None
        self.preprocess = None
        self.device = self._get_device(device)
        self.labels = None
        
        if model_type != 'custom':
            self._load_pretrained_model(model_type)
        elif custom_model_path:
            self._load_custom_model(custom_model_path)
        else:
            raise ValueError("使用自定义模型时必须提供模型路径")
    
    def _get_device(self, device):
        """获取运行设备"""
        if device == 'auto':
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(tf, 'config') and len(tf.config.list_physical_devices('GPU')) > 0:
                return 'cuda'
            else:
                return 'cpu'
        return device
    
    def _load_pretrained_model(self, model_type):
        """加载预训练模型"""
        if model_type in ['resnet50', 'vgg16']:
            # PyTorch模型
            if model_type == 'resnet50':
                self.model = torchvision.models.resnet50(pretrained=True)
                self.model.eval()
                self.model.to(self.device if self.device == 'cuda' else 'cpu')
                
                self.preprocess = transforms.Compose([
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                        std=[0.229, 0.224, 0.225]),
                ])
            elif model_type == 'vgg16':
                self.model = torchvision.models.vgg16(pretrained=True)
                self.model.eval()
                self.model.to(self.device if self.device == 'cuda' else 'cpu')
                
                self.preprocess = transforms.Compose([
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                        std=[0.229, 0.224, 0.225]),
                ])
                
            # 加载ImageNet标签
            try:
                import torchvision.datasets as datasets
                self.labels = datasets.ImageNet(None, split='val').classes
            except:
                # 如果无法直接加载，使用备用方法
                self.labels = self._load_imagenet_labels()
                
        else:
            # TensorFlow/Keras模型
            tf.keras.backend.clear_session()
            
            if model_type == 'mobilenetv2':
                self.model = MobileNetV2(weights='imagenet')
                input_shape = (224, 224)
            elif model_type == 'inceptionv3':
                self.model = InceptionV3(weights='imagenet')
                input_shape = (299, 299)
            elif model_type == 'xception':
                self.model = Xception(weights='imagenet')
                input_shape = (299, 299)
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")
            
            self.preprocess = self._get_keras_preprocess(input_shape)
    
    def _load_custom_model(self, model_path):
        """加载自定义模型"""
        # 尝试作为PyTorch模型加载
        try:
            self.model = torch.load(model_path, map_location=self.device if self.device == 'cuda' else 'cpu')
            self.model.eval()
            self.preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                    std=[0.229, 0.224, 0.225]),
            ])
            return
        except:
            pass
            
        # 尝试作为Keras模型加载
        try:
            self.model = tf.keras.models.load_model(model_path)
            input_shape = self.model.input_shape[1:3]
            self.preprocess = self._get_keras_preprocess(input_shape)
            return
        except:
            pass
            
        raise ValueError(f"无法加载自定义模型: {model_path}")
    
    def _get_keras_preprocess(self, input_shape):
        """获取Keras模型的预处理函数"""
        def preprocess(img):
            img = cv2.resize(img, input_shape)
            img = img.astype(np.float32) / 255.0
            img = np.expand_dims(img, axis=0)
            return img
        return preprocess
    
    def _load_imagenet_labels(self):
        """加载ImageNet标签"""
        # 使用简化的ImageNet 1000类标签
        labels = [
            "tench, Tinca tinca", "goldfish, Carassius auratus", "great white shark, white shark, man-eater, man-eating shark, Carcharodon carcharias",
            "tiger shark, Galeocerdo cuvieri", "hammerhead, hammerhead shark", "electric ray, crampfish, numbfish, torpedo",
            "stingray", "cock", "hen", "ostrich, Struthio camelus",
            "brambling, Fringilla montifringilla", "goldfinch, Carduelis carduelis", "house finch, linnet, Carpodacus mexicanus",
            "junco, snowbird", "indigo bunting, indigo finch, indigo bird, Passerina cyanea", "robin, American robin, Turdus migratorius",
            "bulbul", "jay", "magpie", "chickadee",
            "water ouzel, dipper", "kite", "bald eagle, American eagle, Haliaeetus leucocephalus", "vulture",
            "great grey owl, great gray owl, Strix nebulosa", "European fire salamander, Salamandra salamandra", "common newt, Triturus vulgaris",
            "eft", "spotted salamander, Ambystoma maculatum", "axolotl, mud puppy, Ambystoma mexicanum",
            "bullfrog, Rana catesbeiana", "tree frog, tree-frog", "tailed frog, bell toad, ribbed toad, tailed toad, Ascaphus trui",
            "loggerhead, loggerhead turtle, Caretta caretta", "leatherback turtle, leatherback, leathery turtle, Dermochelys coriacea", "mud turtle",
            "terrapin", "box turtle, box tortoise", "banded gecko", "common iguana, iguana, Iguana iguana",
            "American chameleon, anole, Anolis carolinensis", "whiptail, whiptail lizard", "agama", "frilled lizard, Chlamydosaurus kingi",
            "alligator lizard", "Gila monster, Heloderma suspectum", "green lizard, Lacerta viridis", "African chameleon, Chamaeleo chamaeleon",
            "Komodo dragon, Komodo lizard, dragon lizard, giant lizard, Varanus komodoensis", "African crocodile, Nile crocodile, Crocodylus niloticus", "American alligator, Alligator mississipiensis",
            "triceratops", "thunder snake, worm snake, Carphophis amoenus", "ringneck snake, ring-necked snake, ring snake",
            "hognose snake, puff adder, sand viper", "green snake, grass snake", "king snake, kingsnake", "garter snake, grass snake",
            "water snake", "vine snake", "night snake, Hypsiglena torquata", "boa constrictor, Constrictor constrictor",
            "rock python, rock snake, Python sebae", "Indian cobra, Naja naja", "green mamba", "sea snake",
            "horned viper, cerastes, sand viper, horned asp, Cerastes cornutus", "diamondback, diamondback rattlesnake, Crotalus adamanteus", "sidewinder, horned rattlesnake, Crotalus cerastes",
            "trilobite", "harvestman, daddy longlegs, Phalangium opilio", "scorpion", "black and gold garden spider, Argiope aurantia",
            "barn spider, Araneus cavaticus", "garden spider, Aranea diademata", "black widow, Latrodectus mactans", "tarantula",
            "wolf spider, hunting spider", "tick", "centipede", "black grouse", "ptarmigan",
            "ruffed grouse, partridge, Bonasa umbellus", "prairie chicken, prairie grouse, prairie fowl", "peacock", "quail",
            "partridge", "African grey, African gray, Psittacus erithacus", "macaw", "sulphur-crested cockatoo, Kakatoe galerita, Cacatua galerita",
            "lorikeet", "coucal", "bee eater", "hornbill", "hummingbird",
            "jacamar", "toucan", "drake", "red-breasted merganser, Mergus serrator", "goose",
            "black swan, Cygnus atratus", "tusker", "echidna, spiny anteater, anteater", "platypus, duckbill, duckbilled platypus, duck-billed platypus, Ornithorhynchus anatinus",
            "wallaby, brush kangaroo", "koala, koala bear, kangaroo bear, native bear, Phascolarctos cinereus", "wombat", "jellyfish",
            "sea anemone, anemone", "brain coral", "flatworm, platyhelminth", "nematode, nematode worm, roundworm",
            "conch", "snail", "slug", "sea slug, nudibranch", "chiton, coat-of-mail shell, sea cradle, polyplacophore",
            "chambered nautilus, pearly nautilus, nautilus", "Dungeness crab, Cancer magister", "rock crab, Cancer irroratus", "fiddler crab",
            "king crab, Alaska crab, Alaskan king crab, Alaska king crab, Paralithodes camtschatica", "American lobster, Northern lobster, Maine lobster, Homarus americanus", "spiny lobster, langouste, rock lobster, crawfish, crayfish, sea crawfish",
            "crayfish, crawfish, crawdad, crawdaddy", "hermit crab", "isopod", "white stork, Ciconia ciconia", "black stork, Ciconia nigra",
            "spoonbill", "flamingo", "little blue heron, Egretta caerulea", "great blue heron, Ardea herodias", "American egret, great white heron, Egretta albus",
            "bittern", "crane", "limpkin, Aramus pictus", "European gallinule, Porphyrio porphyrio", "American coot, marsh hen, mud hen, water hen, Fulica americana",
            "bustard", "ruddy turnstone, Arenaria interpres", "red-backed sandpiper, dunlin, Erolia alpina", "redshank, Tringa totanus", "dowitcher",
            "oystercatcher, oyster catcher", "pelican", "king penguin, Aptenodytes patagonica", "albatross, mollymawk", "grey whale, gray whale, devilfish, Eschrichtius gibbosus, Eschrichtius robustus",
            "killer whale, killer, orca, grampus, sea wolf, Orcinus orca", "dugong, Dugong dugon", "sea lion", "Chihuahua", "Japanese spaniel",
            "Maltese dog, Maltese terrier, Maltese", "Pekinese, Pekingese, Peke", "Shih-Tzu", "Blenheim spaniel", "papillon",
            "toy terrier", "Rhodesian ridgeback", "Afghan hound, Afghan", "basset, basset hound", "beagle",
            "bloodhound, sleuthhound", "bluetick", "black-and-tan coonhound", "Walker hound, Walker foxhound", "English foxhound",
            "redbone", "borzoi, Russian wolfhound", "Irish wolfhound", "Italian greyhound", "whippet",
            "Ibizan hound, Ibizan Podenco", "Norwegian elkhound, elkhound", "otterhound, otter hound", "Saluki, gazelle hound", "Scottish deerhound, deerhound",
            "Weimaraner", "Staffordshire bullterrier, Staffordshire bull terrier", "American Staffordshire terrier, Staffordshire terrier, American pit bull terrier, pit bull terrier", "Bedlington terrier", "Border terrier",
            "Kerry blue terrier", "Irish terrier", "Norfolk terrier", "Norwich terrier", "Yorkshire terrier",
            "wire-haired fox terrier", "Lakeland terrier", "Sealyham terrier, Sealyham", "Airedale, Airedale terrier", "cairn, cairn terrier",
            "Australian terrier", "Dandie Dinmont, Dandie Dinmont terrier", "Boston bull, Boston terrier", "miniature schnauzer", "giant schnauzer",
            "standard schnauzer", "Scotch terrier, Scottish terrier, Scottie", "Tibetan terrier, chrysanthemum dog", "silky terrier, Sydney silky", "soft-coated wheaten terrier",
            "West Highland white terrier", "Lhasa, Lhasa apso", "flat-coated retriever", "curly-coated retriever", "golden retriever",
            "Labrador retriever", "Chesapeake Bay retriever", "German short-haired pointer", "vizsla, Hungarian pointer", "English setter",
            "Irish setter, red setter", "Gordon setter", "Brittany spaniel", "clumber, clumber spaniel", "English springer, English springer spaniel",
            "Welsh springer spaniel", "cocker spaniel, English cocker spaniel, cocker", "Sussex spaniel", "Irish water spaniel", "kuvasz",
            "schipperke", "groenendael", "malinois", "briard", "kelpie",
            "komondor", "Old English sheepdog, bobtail", "Shetland sheepdog, Shetland sheep dog, Shetland", "collie", "Border collie",
            "Bouvier des Flandres, Bouviers des Flandres", "Rottweiler", "German shepherd, German shepherd dog, German police dog, alsatian", "Doberman, Doberman pinscher", "miniature pinscher",
            "Greater Swiss Mountain dog", "Bernese mountain dog", "Appenzeller", "EntleBucher", "boxer",
            "bull mastiff", "Tibetan mastiff", "French bulldog", "Great Dane", "Saint Bernard, St Bernard",
            "Eskimo dog, husky", "malamute, Alaskan malamute", "Siberian husky", "dalmatian, coach dog, carriage dog", "affenpinscher, monkey pinscher, monkey dog",
            "basenji", "pug, pug-dog", "Leonberg", "Newfoundland, Newfoundland dog", "Great Pyrenees",
            "Samoyed, Samoyede", "Pomeranian", "chow, chow chow", "keeshond", "Brabancon griffon",
            "Pembroke, Pembroke Welsh corgi", "Cardigan, Cardigan Welsh corgi", "toy poodle", "miniature poodle", "standard poodle",
            "Mexican hairless", "timber wolf, grey wolf, gray wolf, Canis lupus", "white wolf, Arctic wolf, Canis lupus tundrarum", "red wolf, maned wolf, Canis rufus, Canis niger", "coyote, prairie wolf, brush wolf, Canis latrans",
            "dingo, warrigal, warragal, Canis dingo", "dhole, Cuon alpinus", "African hunting dog, hyena dog, Cape hunting dog, Lycaon pictus", "hyena, hyaena", "red fox, Vulpes vulpes",
            "kit fox, Vulpes macrotis", "Arctic fox, white fox, Alopex lagopus", "grey fox, gray fox, Urocyon cinereoargenteus", "tabby, tabby cat", "tiger cat",
            "Persian cat", "Siamese cat, Siamese", "Egyptian cat", "cougar, puma, catamount, mountain lion, painter, panther, Felis concolor", "lynx, catamount",
            "leopard, Panthera pardus", "snow leopard, ounce, Panthera uncia", "jaguar, panther, Panthera onca, Felis onca", "lion, king of beasts, Panthera leo", "tiger, Panthera tigris",
            "cheetah, chetah, Acinonyx jubatus", "brown bear, bruin, Ursus arctos", "American black bear, black bear, Ursus americanus, Euarctos americanus", "ice bear, polar bear, Ursus Maritimus, Thalarctos maritimus", "sloth bear, Melursus ursinus, Ursus ursinus",
            "mongoose", "meerkat, mierkat", "tiger beetle", "ladybug, ladybeetle, lady beetle, ladybird, ladybird beetle", "ground beetle, carabid beetle",
            "long-horned beetle, longicorn, longicorn beetle", "leaf beetle, chrysomelid", "dung beetle", "rhinoceros beetle", "weevil",
            "fly", "bee", "ant, emmet, pismire", "grasshopper, hopper", "cricket",
            "walking stick, walkingstick, stick insect", "cockroach, roach", "praying mantis, mantis", "cicada, cicala", "leafhopper",
            "lacewing, lacewing fly", "dragonfly, darning needle, devil's darning needle, sewing needle, snake feeder, snake doctor, mosquito hawk, skeeter hawk", "damselfly", "admiral",
            "ringlet, ringlet butterfly", "monarch, monarch butterfly, milkweed butterfly, Danaus plexippus", "cabbage butterfly", "sulphur butterfly, sulfur butterfly", "lycaenid, lycaenid butterfly",
            "starfish, sea star", "sea urchin", "sea cucumber, holothurian", "wood rabbit, cottontail, cottontail rabbit", "hare",
            "Angora, Angora rabbit", "hamster", "porcupine, hedgehog", "fox squirrel, eastern fox squirrel, Sciurus niger", "marmot",
            "beaver", "guinea pig, Cavia cobaya", "sorrel", "zebra", "hog, pig, grunter, squealer, Sus scrofa",
            "wild boar, boar, Sus scrofa", "warthog", "hippopotamus, hippo, river horse, Hippopotamus amphibius", "ox", "water buffalo, water ox, Asiatic buffalo, Bubalus bubalis",
            "bison", "ram, tup", "bighorn, bighorn sheep, cimarron, Rocky Mountain bighorn, Rocky Mountain sheep, Ovis canadensis", "ibex, Capra ibex", "hartebeest",
            "impala, Aepyceros melampus", "gazelle", "Arabian camel, dromedary, Camelus dromedarius", "llama", "weasel",
            "mink", "polecat, fitch, foulmart, foumart, Mustela putorius", "black-footed ferret, ferret, Mustela nigripes", "otter", "skunk, polecat, wood pussy",
            "badger", "armadillo", "three-toed sloth, ai, Bradypus tridactylus", "orangutan, orang, orangutang, Pongo pygmaeus", "gorilla, Gorilla gorilla",
            "chimpanzee, chimp, Pan troglodytes", "gibbon, Hylobates lar", "siamang, Hylobates syndactylus, Symphalangus syndactylus", "guenon, guenon monkey", "patas, hussar monkey, Erythrocebus patas",
            "baboon", "macaque", "langur", "colobus, colobus monkey", "proboscis monkey, Nasalis larvatus",
            "marmoset", "capuchin, ringtail, Cebus capucinus", "howler monkey, howler", "titi, titi monkey", "spider monkey, Ateles geoffroyi",
            "squirrel monkey, Saimiri sciureus", "Madagascar cat, ring-tailed lemur, Lemur catta", "indri, indris, Indri indri, Indri brevicaudatus", "Indian elephant, Elephas maximus", "African elephant, Loxodonta africana",
            "lesser panda, red panda, panda, bear cat, cat bear, Ailurus fulgens", "giant panda, panda, panda bear, coon bear, Ailuropoda melanoleuca", "barracouta, snoek", "eel", "coho, coho salmon, blue jack, silver salmon, Oncorhynchus kisutch",
            "rock beauty, Holocanthus tricolor", "anemone fish", "sturgeon", "gar, garfish, garpike, billfish, Lepisosteus osseus", "lionfish",
            "puffer, pufferfish, blowfish, globefish", "abacus", "abaya", "academic gown, academic robe, judge's robe", "accordion, piano accordion, squeeze box",
            "acoustic guitar", "aircraft carrier, carrier, flattop, attack aircraft carrier", "airliner", "airship, dirigible", "altar",
            "ambulance", "amphibian, amphibious vehicle", "analog clock", "apiary, bee house", "apron",
            "ashcan, trash can, garbage can, wastebin, ash bin, ash-bin, ashbin, dustbin, trash barrel, trash bin", "assault rifle, assault gun", "backpack, back pack, knapsack, packsack, rucksack, haversack", "bakery, bakeshop, bakehouse", "balance beam, beam",
            "balloon", "ballpoint, ballpoint pen, ballpen, Biro", "Band Aid", "banjo", "bannister, banister, balustrade, balusters, handrail",
            "barbell", "barber chair", "barbershop", "barn", "barometer",
            "barrel, cask", "barrow, garden cart, lawn cart, wheelbarrow", "baseball", "basketball", "bassinet",
            "bassoon", "bathing cap, swimming cap", "bath towel", "bathtub, bathing tub, bath, tub", "beach wagon, station wagon, wagon, estate car, beach waggon, station waggon, waggon",
            "beacon, lighthouse, beacon light, pharos", "beaker", "bearskin, busby, shako", "beer bottle", "beer glass",
            "bell", "bell cote, bell cot", "bib", "bicycle-built-for-two, tandem bicycle, tandem", "bikini, two-piece",
            "binder, ring-binder", "binoculars, field glasses, opera glasses", "birdhouse", "boathouse", "bobsled, bobsleigh, bob",
            "bolo tie, bolo, bola tie, bola", "bonnet, poke bonnet", "book", "bookcase", "bookshop, bookstore, bookstall",
            "bottlecap", "bow", "bow tie, bow-tie, bowtie", "brass, memorial tablet, plaque", "brassiere, bra, bandeau",
            "breakwater, groin, groyne, mole, bulwark, seawall, jetty", "breastplate, aegis, egis", "broom", "bucket, pail", "buckle",
            "bulletproof vest", "bullet train, bullet", "butcher shop, meat market", "cab, hack, taxi, taxicab", "caldron, cauldron",
            "candle", "cannon", "canoe", "can opener, tin opener", "cardigan",
            "car mirror", "carousel, carrousel, merry-go-round, roundabout, whirligig", "carpenter's kit, tool kit", "carton", "car wheel",
            "cash machine, cash dispenser, automated teller machine, automatic teller machine, automated teller, automatic teller, ATM", "cassette", "cassette player", "castle", "catamaran",
            "CD player", "cello, violoncello", "cellular telephone, cellular phone, cellphone, cell, mobile phone", "chain", "chainlink fence",
            "chain mail, ring mail, mail, chain armor, chain armour, ring armor, ring armour", "chain saw, chainsaw", "chest", "chiffonier, commode", "chime, bell, gong",
            "china cabinet, china closet", "Christmas stocking", "church, church building", "cinema, movie theater, movie theatre, movie house, picture palace", "cleaver, meat cleaver, chopper",
            "cliff dwelling", "cloak", "clog, geta, patten, sabot", "cocktail shaker", "coffee mug",
            "coffeepot", "coil, spiral, volute, whorl, helix", "combination lock", "computer keyboard, keypad", "conch",
            "corkscrew, bottle screw", "cornet, horn, trumpet, trump", "cowboy boot", "cowboy hat, ten-gallon hat", "cradle",
            "crane", "crash helmet", "crate", "crib, cot", "Crock Pot",
            "croquet ball", "crutch", "cuirass", "dam, dike, dyke", "desk",
            "desktop computer", "dial telephone, dial phone", "diaper, nappy, napkin", "digital clock", "digital watch",
            "dining table, board", "dishrag, dishcloth", "dishwasher, dish washer, dishwashing machine", "disk brake, disc brake", "dock, dockage, docking facility",
            "dogsled, dog sled, dog sleigh", "dome", "doormat, welcome mat", "drilling platform, offshore rig", "drum, membranophone, tympan",
            "drumstick", "dumbbell", "Dutch oven", "electric fan, blower", "electric guitar",
            "electric locomotive", "entertainment center", "envelope", "espresso maker", "face powder",
            "feather boa, boa", "file, file cabinet, filing cabinet", "fireboat", "fire engine, fire truck", "fire screen, fireguard",
            "flagpole, flagstaff", "flute, transverse flute", "folding chair", "football helmet", "forklift",
            "fountain", "fountain pen", "four-poster", "freight car", "French horn, horn",
            "frying pan, frypan, skillet", "fur coat", "garbage truck, dustcart", "gasmask, respirator, gas helmet", "gas pump, gasoline pump, petrol pump, island dispenser",
            "goblet", "go-kart, kart", "golf ball", "golfcart, golf cart", "gondola",
            "gong, tam-tam", "gown", "grand piano, grand", "greenhouse, nursery, glasshouse", "grille, radiator grille",
            "grocery store, grocery, food market, market", "guillotine", "hair slide", "hair spray", "half track",
            "hammer", "hamper", "hand blower, blow dryer, blow drier, hair dryer, hair drier", "hand-held computer, hand-held microcomputer", "handkerchief, hankie, hanky, hankey",
            "hard disc, hard disk, fixed disk", "harmonica, mouth organ, harp, mouth harp", "harp", "harvester, reaper", "hatchet",
            "holster", "home theater, home theatre", "honeycomb", "hook, claw", "hoopskirt, crinoline",
            "horizontal bar, high bar", "horse cart, horse-cart", "hourglass", "iPod", "iron, smoothing iron",
            "jack-o'-lantern", "jean, blue jean, denim", "jeep, landrover", "jersey, T-shirt, tee shirt", "jigsaw puzzle",
            "jinrikisha, ricksha, rickshaw", "joystick", "kimono", "knee pad", "knot",
            "lab coat, laboratory coat", "ladle", "lampshade, lamp shade", "laptop, laptop computer", "lawn mower, mower",
            "lens cap, lens cover", "letter opener, paper knife, paperknife", "library", "lifeboat", "lighter, light, igniter, ignitor",
            "limousine, limo", "liner, ocean liner", "lipstick", "Loafer", "lotion",
            "loudspeaker, speaker, speaker unit, loudspeaker system, speaker system", "loupe, jeweler's loupe", "lumbermill, sawmill", "magnetic compass", "mailbag, postbag",
            "mailbox, letter box", "maillot", "maillot, tank suit", "manhole cover", "maraca",
            "marimba, xylophone", "mask", "matchstick", "maypole", "maze, labyrinth",
            "measuring cup", "medicine chest, medicine cabinet", "megalith, megalithic structure", "microphone, mike", "microwave, microwave oven",
            "military uniform", "milk can", "minibus", "miniskirt, mini", "minivan",
            "missile", "mitten", "mixing bowl", "mobile home, manufactured home", "Model T",
            "modem", "monastery", "monitor", "moped", "mortar",
            "mortarboard", "mosque", "mosquito net", "motor scooter, scooter", "mountain bike, all-terrain bike, off-roader",
            "mountain tent", "mouse, computer mouse", "mousetrap", "moving van", "muzzle",
            "nail", "neck brace", "necklace", "nipple", "notebook, notebook computer",
            "obelisk", "oboe, hautboy, hautbois", "ocarina, sweet potato", "odometer, hodometer, mileometer, milometer", "oil filter",
            "organ, pipe organ", "oscilloscope, scope, cathode-ray oscilloscope, CRO", "overskirt", "oxcart", "oxygen mask",
            "packet", "paddle, boat paddle", "paddlewheel, paddle wheel", "padlock", "paintbrush",
            "pajama, pyjama, pj's, jammies", "palace", "panpipe, pandean pipe, syrinx", "paper towel", "parachute, chute",
            "parallel bars, bars", "park bench", "parking meter", "passenger car, coach, carriage", "patio, terrace",
            "pay-phone, pay-station", "pedestal, plinth, footstall", "pencil", "pencil box, pencil case", "pencil sharpener",
            "perfume, essence", "Petri dish", "photocopier", "pick, plectrum, plectron", "pickelhaube",
            "picket fence, paling", "pickup, pickup truck", "pier", "piggy bank, penny bank", "pill bottle",
            "pillow", "ping-pong ball", "pinwheel", "pirate, pirate ship", "pitcher, ewer",
            "plane, carpenter's plane, woodworking plane", "planetarium", "plastic bag", "plate rack", "plow, plough",
            "plunger, plumber's helper", "Polaroid camera, Polaroid Land camera", "pole", "police van, police wagon, paddy wagon, patrol wagon, wagon, black Maria", "poncho",
            "pool table, billiard table, snooker table", "pop bottle, soda bottle", "pot, flowerpot", "potter's wheel", "power drill",
            "prayer rug, prayer mat", "printer", "prison, prison house", "projectile, missile", "projector",
            "puck, hockey puck", "punching bag, punch bag, punching ball, punchball", "purse", "quill, quill pen", "quilt, comforter, comfort, puff",
            "racer, race car, racing car", "racket, racquet", "radiator", "radio, wireless", "radio telescope, radio reflector",
            "rain barrel", "recreational vehicle, RV, R.V.", "reel", "reflex camera", "refrigerator, icebox",
            "remote control, remote", "restaurant, eating house, eating place, eatery", "revolver, six-gun, six-shooter", "rifle", "rocking chair, rocker",
            "rotisserie", "rubber eraser, rubber, pencil eraser", "rugby ball", "rule, ruler", "running shoe",
            "safe", "safety pin", "saltshaker, salt shaker", "sandal", "sarong",
            "sax, saxophone", "scabbard", "scale, weighing machine", "school bus", "schooner",
            "scoreboard", "screen, CRT screen", "screw", "screwdriver", "seat belt, seatbelt",
            "sewing machine", "shield, buckler", "shoe shop, shoe-shop, shoe store", "shoji", "shopping basket",
            "shopping cart", "shovel", "shower cap", "shower curtain", "ski",
            "ski mask", "sleeping bag", "slide rule, slipstick", "sliding door", "slot, one-armed bandit",
            "snorkel", "snowmobile", "snowplow, snowplough", "soap dispenser", "soccer ball",
            "sock", "solar dish, solar collector, solar furnace", "sombrero", "soup bowl", "space bar",
            "space heater", "space shuttle", "spatula", "speedboat", "spider web, spider's web",
            "spindle", "sports car, sport car", "spotlight, spot", "stage", "steam locomotive",
            "steel arch bridge", "steel drum", "stethoscope", "stole", "stone wall",
            "stopwatch, stop watch", "stove", "strainer", "streetcar, tram, tramcar, trolley, trolley car", "stretcher",
            "studio couch, day bed", "stupa, tope", "submarine, pigboat, sub, U-boat", "suit, suit of clothes", "sundial",
            "sunglass", "sunglasses, dark glasses, shades", "sunscreen, sunblock, sun blocker", "suspension bridge", "swab, swob, mop",
            "sweatshirt", "swimming trunks, bathing trunks", "swing", "switch, electric switch, electrical switch", "syringe",
            "table lamp", "tank, army tank, armored combat vehicle, armoured combat vehicle", "tape player", "teapot", "teddy, teddy bear",
            "television, television system", "tennis ball", "tennis court", "tennis racket, tennis racquet", "tent",
            "theater curtain, theatre curtain", "thimble", "thresher, thrasher, threshing machine", "throne", "tile roof",
            "toaster", "tobacco shop, tobacconist shop, tobacconist", "toilet seat", "torch", "totem pole",
            "tow truck, tow car, wrecker", "toyshop", "tractor", "trailer truck, tractor trailer, trucking rig, rig, articulated lorry, semi", "tray",
            "trench coat", "tricycle, trike, velocipede", "trimaran", "tripod", "triumphal arch",
            "trolleybus, trolley coach, trackless trolley", "trombone", "tub, vat", "turnstile", "typewriter keyboard",
            "umbrella", "unicycle, monocycle", "upright, upright piano", "vacuum, vacuum cleaner", "vase",
            "vault", "velvet", "vending machine", "vestment", "viaduct",
            "violin, fiddle", "volleyball", "waffle iron", "wall clock", "wallet, billfold, notecase, pocketbook",
            "wardrobe, closet, press", "warplane, military plane", "washtub", "water bottle", "water jug",
            "water tower", "whiskey jug", "whistle", "wig", "window screen",
            "window shade", "Windsor tie", "wine bottle", "wing", "wok",
            "wooden spoon", "wool, woolen, woollen", "worm fence, snake fence, snake-rail fence, Virginia fence", "wreck, shipwreck", "yawl",
            "yurt", "web site, website, internet site, site", "comic book", "crossword puzzle, crossword", "street sign",
            "traffic light, traffic signal, stoplight", "book jacket, dust cover, dust jacket, dust wrapper", "menu", "plate", "guacamole",
            "consomme", "hot pot, hotpot", "trifle", "ice cream, icecream", "ice lolly, lolly, lollipop, popsicle",
            "French loaf", "bagel, beigel", "pretzel", "cheeseburger", "hotdog, hot dog, red hot",
            "mashed potato", "head cabbage", "broccoli", "cauliflower", "zucchini, courgette",
            "spaghetti squash", "acorn squash", "butternut squash", "cucumber, cuke", "artichoke, globe artichoke",
            "bell pepper", "cardoon", "mushroom", "Granny Smith", "strawberry",
            "orange", "lemon", "fig", "pineapple, ananas", "banana",
            "jackfruit, jak, jack", "cherimoya, cherimolla, custard apple", "pomegranate", "hay", "carbonara",
            "chocolate sauce, chocolate syrup", "dough", "meat loaf, meatloaf", "pizza, pizza pie", "potpie",
            "burrito", "red wine", "espresso", "cup", "eggnog",
            "alp", "bubble", "cliff, drop, drop-off", "coral reef", "geyser",
            "lakeside, lakeshore", "promontory, headland, head, foreland", "sandbar, sand bar", "seashore, coast, seacoast, sea-coast", "valley, vale",
            "volcano", "ballplayer, baseball player", "groom, bridegroom", "scuba diver", "rapeseed",
            "daisy", "yellow lady's slipper, yellow lady-slipper, Cypripedium calceolus, Cypripedium parviflorum", "corn", "acorn", "hip, rose hip, rosehip",
            "buckeye, horse chestnut, conker", "coral fungus", "agaric", "gyromitra", "stinkhorn, carrion fungus",
            "earthstar", "hen-of-the-woods, hen of the woods, Polyporus frondosus, Grifola frondosa", "bolete", "ear, spike, capitulum", "toilet tissue, toilet paper, bathroom tissue"
        ]
        return labels
    
    def classify(self, image_path, top_k=5):
        """
        对图像进行分类
        
        Args:
            image_path: 图像路径
            top_k: 返回前k个预测结果
            
        Returns:
            分类结果字典
        """
        # 读取图像
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        # 预处理
        if self.model_type in ['resnet50', 'vgg16', 'custom'] and isinstance(self.model, torch.nn.Module):
            # PyTorch推理
            img_pil = Image.open(image_path).convert('RGB')
            img_tensor = self.preprocess(img_pil).unsqueeze(0)
            img_tensor = img_tensor.to(self.device if self.device == 'cuda' else 'cpu')
            
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.nn.functional.softmax(outputs, dim=1)
                top_probs, top_indices = probs.topk(top_k)
            
            # 转换为numpy格式
            top_probs = top_probs.cpu().numpy()[0]
            top_indices = top_indices.cpu().numpy()[0]
            
            results = []
            for i in range(top_k):
                if self.labels and i < len(self.labels) and top_indices[i] < len(self.labels):
                    label = self.labels[top_indices[i]]
                else:
                    label = f"Class {top_indices[i]}"
                results.append({
                    'class': label,
                    'confidence': float(top_probs[i])
                })
                
        else:
            # TensorFlow/Keras推理
            img_preprocessed = self.preprocess(img)
            
            if hasattr(self.model, 'predict'):
                predictions = self.model.predict(img_preprocessed)
                # 对于ImageNet预训练模型
                if self.model_type in ['mobilenetv2', 'inceptionv3', 'xception']:
                    decoded = decode_predictions(predictions, top=top_k)[0]
                    results = [
                        {
                            'class': f"{item[1]} ({item[2]})".replace('_', ' '),
                            'confidence': float(item[2])
                        }
                        for item in decoded
                    ]
                else:
                    # 自定义模型
                    top_indices = np.argsort(predictions[0])[-top_k:][::-1]
                    top_probs = predictions[0][top_indices]
                    results = [
                        {
                            'class': f"Class {idx}",
                            'confidence': float(prob)
                        }
                        for idx, prob in zip(top_indices, top_probs)
                    ]
            else:
                raise ValueError("模型不支持predict方法")
        
        return results
    
    def visualize_result(self, image_path, results, output_path=None):
        """
        可视化分类结果
        
        Args:
            image_path: 图像路径
            results: 分类结果
            output_path: 输出图像路径
            
        Returns:
            处理后的图像
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        # 在图像上绘制结果
        h, w = img.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        color = (0, 255, 0)  # 绿色
        thickness = 2
        
        # 添加标题
        cv2.putText(img, "Classification Results", (10, 30), font, font_scale, color, thickness)
        
        # 添加预测结果
        for i, result in enumerate(results):
            text = f"{result['class'].split(',')[0]}: {result['confidence']:.2%}"
            y_pos = 60 + i * 30
            
            # 确保文本不超出图像范围
            if y_pos < h - 10:
                cv2.putText(img, text, (10, y_pos), font, font_scale, color, thickness)
        
        # 保存结果图像
        if output_path:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            cv2.imwrite(output_path, img)
        
        return img
    
    def export_results(self, results_dict, output_path, format='json'):
        """
        导出分类结果
        
        Args:
            results_dict: 包含文件路径和分类结果的字典
            output_path: 输出文件路径
            format: 输出格式，支持'json', 'csv', 'txt'
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, indent=2, ensure_ascii=False)
        elif format == 'csv':
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['File Path', 'Top 1 Class', 'Top 1 Confidence', 'Top 2 Class', 'Top 2 Confidence', 'Top 3 Class', 'Top 3 Confidence'])
                for file_path, results in results_dict.items():
                    row = [file_path]
                    for i in range(3):
                        if i < len(results):
                            row.extend([results[i]['class'], results[i]['confidence']])
                        else:
                            row.extend(['', ''])
                    writer.writerow(row)
        elif format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                for file_path, results in results_dict.items():
                    f.write(f"File: {file_path}\n")
                    for i, result in enumerate(results):
                        f.write(f"  {i+1}. {result['class']}: {result['confidence']:.2%}\n")
                    f.write("\n")
        else:
            raise ValueError(f"不支持的输出格式: {format}")

def process_single_image(image_path, classifier, output_dir=None, visualize=False, top_k=5):
    """处理单个图像"""
    try:
        # 分类图像
        results = classifier.classify(image_path, top_k)
        
        # 构建输出文件路径
        base_name = os.path.basename(image_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # 可视化结果
        if visualize and output_dir:
            output_image_path = os.path.join(output_dir, f"{name_without_ext}_classified.jpg")
            classifier.visualize_result(image_path, results, output_image_path)
            print(f"已保存分类可视化结果: {output_image_path}")
        
        return {os.path.abspath(image_path): results}
    except Exception as e:
        print(f"处理图像 {image_path} 时出错: {e}")
        return None

def process_directory(input_dir, classifier, output_dir=None, recursive=False, visualize=False, top_k=5, image_extensions=None):
    """批量处理目录中的图像"""
    if image_extensions is None:
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    all_results = {}
    processed_count = 0
    failed_count = 0
    
    if recursive:
        walk_func = os.walk
    else:
        def walk_func(path):
            yield (path, [], [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    
    for root, _, files in tqdm(walk_func(input_dir), desc="处理进度"):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(root, file)
                result = process_single_image(image_path, classifier, output_dir, visualize, top_k)
                
                if result:
                    all_results.update(result)
                    processed_count += 1
                else:
                    failed_count += 1
    
    print(f"处理完成! 成功: {processed_count}, 失败: {failed_count}")
    return all_results

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='图像分类工具')
    parser.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    parser.add_argument('--output', '-o', default=None, help='输出目录路径')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 模型参数
    parser.add_argument('--model-type', '-m', default='resnet50', 
                      choices=['resnet50', 'vgg16', 'mobilenetv2', 'inceptionv3', 'xception', 'custom'],
                      help='模型类型')
    parser.add_argument('--custom-model', default=None, help='自定义模型路径')
    parser.add_argument('--device', default='auto', choices=['auto', 'cuda', 'cpu'], help='运行设备')
    
    # 分类参数
    parser.add_argument('--top-k', type=int, default=5, help='返回前k个预测结果')
    parser.add_argument('--visualize', '-v', action='store_true', help='可视化分类结果')
    parser.add_argument('--export', '-e', default=None, help='导出结果文件路径')
    parser.add_argument('--export-format', default='json', choices=['json', 'csv', 'txt'], help='导出格式')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 确保输出目录存在
    if args.output and not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # 创建分类器
    try:
        classifier = ImageClassifier(
            model_type=args.model_type,
            device=args.device,
            custom_model_path=args.custom_model
        )
        print(f"已加载 {args.model_type} 模型")
    except Exception as e:
        print(f"加载模型失败: {e}")
        return
    
    # 处理输入
    all_results = {}
    
    if os.path.isfile(args.input):
        # 处理单个文件
        result = process_single_image(args.input, classifier, args.output, args.visualize, args.top_k)
        if result:
            all_results.update(result)
            print(f"\n分类结果:")
            for file_path, results in result.items():
                print(f"文件: {file_path}")
                for i, res in enumerate(results):
                    print(f"  {i+1}. {res['class'].split(',')[0]}: {res['confidence']:.2%}")
    elif os.path.isdir(args.input):
        # 处理目录
        all_results = process_directory(args.input, classifier, args.output, args.recursive, args.visualize, args.top_k)
    else:
        print(f"输入路径不存在: {args.input}")
        return
    
    # 导出结果
    if args.export and all_results:
        classifier.export_results(all_results, args.export, args.export_format)
        print(f"已导出结果到: {args.export}")

if __name__ == "__main__":
    main()
