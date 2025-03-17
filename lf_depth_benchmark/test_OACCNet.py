import argparse
import os.path

import numpy as np

from utils import *
from model import Net


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=str, default='cuda:2')
    parser.add_argument("--angRes", type=int, default=7, help="angular resolution")
    parser.add_argument('--model_name', type=str, default='OACC-Net')
    parser.add_argument('--testset_dir', type=str, default='./demo_input/')
    parser.add_argument('--crop', type=bool, default=True)
    parser.add_argument('--patchsize', type=int, default=128)
    parser.add_argument('--minibatch_test', type=int, default=4)
    parser.add_argument('--model_path', type=str, default='./log/OACC-Net110.pth')
    parser.add_argument('--save_path', type=str, default='./Results/')
    return parser.parse_args()


lf_no_to_name = {
    "HCI": {
        "LF0": "bedroom",
        "LF1": "bicycle",
        "LF2": "herbs",
        "LF3": "dishes"
    },
    "HCI_old": {
        "LF0": "buddha",
        "LF1": "buddha2",
        "LF2": "monasRoom",
        "LF3": "papillon",
        "LF4": "stillLife"
    },
    "Inria_DLFD": {
        'LF0': 'Antiques', 'LF1': 'Big_clock', 'LF2': 'Black&white', 'LF3': 'Blue_room', 'LF4': 'Bottles',
        'LF5': 'Bowl_chair', 'LF6': 'Camera_brush', 'LF7': 'Chess', 'LF8': 'Coffee_beans_vases', 'LF9': 'Coffee_time',
        'LF10': 'Dinosaur', 'LF11': 'Dishes', 'LF12': 'Electro_devices', 'LF13': 'Flowers_clock', 'LF14': 'Flying_dice',
        'LF15': 'Flying_furniture', 'LF16': 'Flying_toys', 'LF17': 'Furniture', 'LF18': 'Green_balloon',
        'LF19': 'Kiwi_bike', 'LF20': 'Lonely_man', 'LF21': 'Microphone', 'LF22': 'Microphone_rooster',
        'LF23': 'Origami', 'LF24': 'Pinenuts_blue', 'LF25': 'Pinenuts_white', 'LF26': 'Robots', 'LF27': 'Rooster_clock',
        'LF28': 'Roses_bed', 'LF29': 'Roses_table', 'LF30': 'Smiling_crowd', 'LF31': 'Smiling_crowd_roses',
        'LF32': 'Three_pillows', 'LF33': 'Toy_bricks', 'LF34': 'Toy_friends', 'LF35': 'Toys', 'LF36': 'Two_vases',
        'LF37': 'White_lamp', 'LF38': 'White_roses'
    }
}

'''
Note: 1) We crop LFs into overlapping patches to save the CUDA memory during inference. 
      2) When cropping is performed, the inference time will be longer than the one reported in our paper.
'''


def disparity_estimation(lf_angCrop, net, cfg):
    if not cfg.crop:
        data = rearrange(lf_angCrop, 'u v h w -> (u h) (v w)')
        data = ToTensor()(data.copy())
        with torch.no_grad():
            disp = net(data.unsqueeze(0).to(cfg.device))
        disp = np.float32(disp[0, 0, :, :].data.cpu())

    else:
        patchsize = cfg.patchsize
        stride = patchsize // 2
        data = torch.from_numpy(lf_angCrop)
        sub_lfs = LFdivide(data.unsqueeze(2), patchsize, stride)
        n1, n2, u, v, c, h, w = sub_lfs.shape
        sub_lfs = rearrange(sub_lfs, 'n1 n2 u v c h w -> (n1 n2) u v c h w')
        mini_batch = cfg.minibatch_test
        num_inference = (n1 * n2) // mini_batch
        with torch.no_grad():
            out_disp = []
            for idx_inference in range(num_inference):
                current_lfs = sub_lfs[idx_inference * mini_batch: (idx_inference + 1) * mini_batch, :, :, :, :, :]
                input_data = rearrange(current_lfs, 'b u v c h w -> b c (u h) (v w)')
                out_disp.append(net(input_data.to(cfg.device)))

            if (n1 * n2) % mini_batch:
                current_lfs = sub_lfs[(idx_inference + 1) * mini_batch:, :, :, :, :, :]
                input_data = rearrange(current_lfs, 'b u v c h w -> b c (u h) (v w)')
                out_disp.append(net(input_data.to(cfg.device)))

        out_disps = torch.cat(out_disp, dim=0)
        out_disps = rearrange(out_disps, '(n1 n2) c h w -> n1 n2 c h w', n1=n1, n2=n2)
        disp = LFintegrate(out_disps, patchsize, patchsize // 2)
        disp = disp[0: data.shape[2], 0: data.shape[3]]
        disp = np.float32(disp.data.cpu())

    return disp


def test(cfg):
    scene_list = os.listdir(cfg.testset_dir)
    angRes = cfg.angRes

    net = Net(cfg.angRes)
    net.to(cfg.device)
    model = torch.load(cfg.model_path, map_location={'cuda:0': cfg.device})
    net.load_state_dict(model['state_dict'])

    for scenes in scene_list:
        print('Working on scene: ' + scenes + '...')
        temp = imageio.imread(cfg.testset_dir + scenes + '/input_Cam000.png')
        lf = np.zeros(shape=(9, 9, temp.shape[0], temp.shape[1], 3), dtype=int)
        for i in range(81):
            temp = imageio.imread(cfg.testset_dir + scenes + '/input_Cam0%.2d.png' % i)
            lf[i // 9, i - 9 * (i // 9), :, :, :] = temp
        lf_gray = np.mean((1 / 255) * lf.astype('float32'), axis=-1, keepdims=False)
        angBegin = (9 - angRes) // 2
        lf_angCrop = lf_gray[angBegin:  angBegin + angRes, angBegin: angBegin + angRes, :, :]

        disp = disparity_estimation(lf_angCrop, net, cfg)
        print('Finished! \n')
        write_pfm(disp, cfg.save_path + '%s.pfm' % (scenes))


def read_lfs(lf_dir, lf_no, ang_res=7):
    print(f"Reading {lf_no}th LFs under directory <{lf_dir}> ...")
    filename_format = r"LF%d_view%d_fine.png"
    filename = filename_format % (lf_no, 0)
    tmp = imageio.imread(os.path.join(lf_dir, filename))
    lf = np.zeros((ang_res, ang_res, tmp.shape[0], tmp.shape[1], 3), dtype=int)
    for i in range(ang_res ** 2):
        tmp = imageio.imread(os.path.join(lf_dir, filename_format % (lf_no, i)))
        lf[i // ang_res, i - ang_res * (i // ang_res), :, :, :] = tmp
    lf_gray = np.mean((1 / 255) * lf.astype('float32'), axis=-1, keepdims=False)
    return lf_gray


def test_benchmark(cfg):
    # TODO: 提供的预训练模型要求是9x9的输入视点, damn!
    net = Net(cfg.angRes)
    net.to(cfg.device)
    model = torch.load(cfg.model_path, map_location={'cuda:0': cfg.device})
    net.load_state_dict(model['state_dict'])

    # SRC_DIR = r"E:\lf\LFRecon\ReconLFs"
    SRC_DIR = r"/data1/cdj/LFRecon/ReconLFs"
    methods = ["GTLF", "GC2ASR", "DispEhcASR", "ELFR", "FS-GAF", "HLFASR", "DistgASR"]
    lf_family = ["HCI", "HCI_old", "Inria_DLFD"]

    for method in methods:
        for lf_f in lf_family:
            lf_path = os.path.join(SRC_DIR, os.path.join(method, lf_f))
            if lf_f == "HCI":
                lf_nos = [i for i in range(4)]
            elif lf_f == "Inria_DLFD":
                lf_nos = [1, 9, 10, 16, 20, 22, 31, 32]
            else:
                lf_nos = [i for i in range(5)]
            print(f"Working on {lf_f} {method}...")
            for lf_no in lf_nos:
                lf_gray = read_lfs(lf_path, lf_no, ang_res=7)
                disp = disparity_estimation(lf_gray, net, cfg)
                lf_no_name = "LF" + str(lf_no)
                # write_pfm(disp, os.path.join(lf_path, f"{lf_no_to_name[lf_f][lf_no_name]}.pfm"))
                write_pfm(disp, os.path.join(lf_path, f"{lf_no_name}.pfm"))  # 不转换成具体的光场名称


if __name__ == '__main__':
    cfg = parse_args()
    test_benchmark(cfg)
