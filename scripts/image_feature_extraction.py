#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像特征提取模块（A6）

功能：
- 传统手工特征提取（HOG、SIFT、SURF、ORB、LBP、Haar-like）
- 深度学习特征提取（使用预训练模型）
- 颜色特征提取（颜色直方图、颜色矩、颜色集）
- 纹理特征提取（GLCM、LBP、Gabor滤波器）
- 特征可视化与导出
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
import torchvision.models as models
import torchvision.transforms as transforms

class FeatureExtractor:
    """图像特征提取器类"""
    
    def __init__(self, device='auto'):
        """
        初始化特征提取器
        
        Args:
            device: 运行设备，'auto', 'cuda', 'cpu'
        """
        self.device = self._get_device(device)
        self.deep_learning_models = {}
    
    def _get_device(self, device):
        """获取运行设备"""
        if device == 'auto':
            return 'cuda' if torch.cuda.is_available() else 'cpu'
        return device
    
    def load_deep_learning_model(self, model_name='resnet50'):
        """
        加载深度学习模型用于特征提取
        
        Args:
            model_name: 模型名称
            
        Returns:
            特征提取模型
        """
        if model_name in self.deep_learning_models:
            return self.deep_learning_models[model_name]
        
        try:
            if model_name == 'resnet50':
                model = models.resnet50(pretrained=True)
                # 移除最后的全连接层
                model = torch.nn.Sequential(*list(model.children())[:-1])
            elif model_name == 'vgg16':
                model = models.vgg16(pretrained=True)
                # 移除最后的分类层
                model = torch.nn.Sequential(*list(model.children())[:-1])
            elif model_name == 'inception_v3':
                model = models.inception_v3(pretrained=True)
                # 移除最后的分类层
                model = torch.nn.Sequential(*list(model.children())[:-1])
            elif model_name == 'mobilenet_v2':
                model = models.mobilenet_v2(pretrained=True)
                # 移除最后的分类层
                model.classifier = torch.nn.Identity()
            else:
                raise ValueError(f"不支持的模型: {model_name}")
            
            model = model.to(self.device)
            model.eval()
            self.deep_learning_models[model_name] = model
            return model
        except Exception as e:
            print(f"加载模型 {model_name} 失败: {e}")
            return None
    
    def extract_hog_features(self, image, orientations=9, pixels_per_cell=(8, 8), cells_per_block=(2, 2)):
        """
        提取HOG（方向梯度直方图）特征
        
        Args:
            image: 输入图像
            orientations: 方向数量
            pixels_per_cell: 每个细胞的像素数
            cells_per_block: 每个块的细胞数
            
        Returns:
            HOG特征向量
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 计算HOG特征
        hog = cv2.HOGDescriptor(
            _winSize=(gray.shape[1] // pixels_per_cell[1] * pixels_per_cell[1],
                     gray.shape[0] // pixels_per_cell[0] * pixels_per_cell[0]),
            _blockSize=(cells_per_block[1] * pixels_per_cell[1],
                       cells_per_block[0] * pixels_per_cell[0]),
            _blockStride=(pixels_per_cell[1], pixels_per_cell[0]),
            _cellSize=(pixels_per_cell[1], pixels_per_cell[0]),
            _nbins=orientations
        )
        
        features = hog.compute(gray)
        return features.flatten()
    
    def extract_sift_features(self, image, n_features=0, contrast_threshold=0.04, edge_threshold=10):
        """
        提取SIFT（尺度不变特征变换）特征
        
        Args:
            image: 输入图像
            n_features: 要保留的最佳特征数量，0表示全部
            contrast_threshold: 对比度阈值
            edge_threshold: 边缘阈值
            
        Returns:
            关键点和描述符
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 创建SIFT对象
        sift = cv2.SIFT_create(nfeatures=n_features, contrastThreshold=contrast_threshold, edgeThreshold=edge_threshold)
        
        # 检测关键点并计算描述符
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def extract_surf_features(self, image, hessian_threshold=100, n_octaves=4, n_octave_layers=3):
        """
        提取SURF（加速稳健特征）特征
        
        Args:
            image: 输入图像
            hessian_threshold: Hessian矩阵阈值
            n_octaves: 金字塔组数
            n_octave_layers: 每组的层数
            
        Returns:
            关键点和描述符
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 创建SURF对象
        try:
            # OpenCV 4.x中SURF需要额外的模块
            surf = cv2.xfeatures2d.SURF_create(hessianThreshold=hessian_threshold, nOctaves=n_octaves, nOctaveLayers=n_octave_layers)
        except AttributeError:
            print("警告: SURF特征需要额外的OpenCV contrib模块")
            return None, None
        
        # 检测关键点并计算描述符
        keypoints, descriptors = surf.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def extract_orb_features(self, image, n_features=500, scale_factor=1.2, n_levels=8):
        """
        提取ORB（Oriented FAST and Rotated BRIEF）特征
        
        Args:
            image: 输入图像
            n_features: 要保留的特征数量
            scale_factor: 金字塔缩放因子
            n_levels: 金字塔层数
            
        Returns:
            关键点和描述符
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 创建ORB对象
        orb = cv2.ORB_create(nfeatures=n_features, scaleFactor=scale_factor, nlevels=n_levels)
        
        # 检测关键点并计算描述符
        keypoints, descriptors = orb.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def extract_lbp_features(self, image, p=8, r=1, method='uniform'):
        """
        提取LBP（局部二值模式）特征
        
        Args:
            image: 输入图像
            p: 采样点数量
            r: 采样半径
            method: LBP方法
            
        Returns:
            LBP特征直方图
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 计算LBP
        lbp = np.zeros_like(gray)
        for i in range(1, gray.shape[0]-1):
            for j in range(1, gray.shape[1]-1):
                center = gray[i, j]
                code = 0
                for k in range(p):
                    # 计算采样点坐标
                    x = i + int(r * np.sin(2 * np.pi * k / p))
                    y = j + int(r * np.cos(2 * np.pi * k / p))
                    # 确保坐标在图像范围内
                    if x >= 0 and x < gray.shape[0] and y >= 0 and y < gray.shape[1]:
                        code |= (gray[x, y] >= center) << (p-1-k)
                lbp[i, j] = code
        
        # 计算直方图
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        
        # 归一化
        hist = hist.astype(float) / np.sum(hist)
        
        return hist
    
    def extract_color_histogram(self, image, bins=8, channels=None):
        """
        提取颜色直方图特征
        
        Args:
            image: 输入图像
            bins: 直方图分箱数
            channels: 要提取的通道，None表示所有通道
            
        Returns:
            颜色直方图特征
        """
        if channels is None:
            channels = [0, 1, 2] if len(image.shape) == 3 else [0]
        
        histograms = []
        for channel in channels:
            hist = cv2.calcHist([image], [channel], None, [bins], [0, 256])
            histograms.extend(hist.flatten())
        
        # 归一化
        histograms = np.array(histograms)
        histograms = histograms / np.sum(histograms) if np.sum(histograms) > 0 else histograms
        
        return histograms
    
    def extract_color_moments(self, image):
        """
        提取颜色矩特征（一阶矩、二阶矩、三阶矩）
        
        Args:
            image: 输入图像
            
        Returns:
            颜色矩特征
        """
        moments = []
        
        if len(image.shape) == 3:
            # 彩色图像，分别计算每个通道
            for channel in range(3):
                # 一阶矩（均值）
                mean = np.mean(image[:, :, channel])
                # 二阶矩（标准差）
                std = np.std(image[:, :, channel])
                # 三阶矩（偏度）
                skewness = np.mean(((image[:, :, channel] - mean) / std) ** 3) if std > 0 else 0
                moments.extend([mean, std, skewness])
        else:
            # 灰度图像
            mean = np.mean(image)
            std = np.std(image)
            skewness = np.mean(((image - mean) / std) ** 3) if std > 0 else 0
            moments.extend([mean, std, skewness])
        
        return np.array(moments)
    
    def extract_glcm_features(self, image, distances=[1], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4], levels=256):
        """
        提取GLCM（灰度共生矩阵）特征
        
        Args:
            image: 输入图像
            distances: 距离列表
            angles: 角度列表
            levels: 灰度级别
            
        Returns:
            GLCM特征向量
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 确保灰度图在合适的范围内
        if levels <= 256:
            max_val = levels - 1
            gray = np.clip((gray * max_val / 255).astype(np.uint8), 0, max_val)
        
        features = []
        
        # 计算GLCM
        for d in distances:
            for angle in angles:
                # 使用skimage的graycomatrix函数（如果可用）
                try:
                    from skimage.feature import graycomatrix, graycoprops
                    glcm = graycomatrix(gray, distances=[d], angles=[angle], levels=levels, symmetric=True, normed=True)
                    
                    # 计算GLCM属性
                    contrast = graycoprops(glcm, 'contrast')[0, 0]
                    dissimilarity = graycoprops(glcm, 'dissimilarity')[0, 0]
                    homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
                    energy = graycoprops(glcm, 'energy')[0, 0]
                    correlation = graycoprops(glcm, 'correlation')[0, 0]
                    
                    features.extend([contrast, dissimilarity, homogeneity, energy, correlation])
                except ImportError:
                    print("警告: GLCM特征需要scikit-image库")
                    return None
        
        return np.array(features)
    
    def extract_gabor_features(self, image, frequencies=[0.1, 0.2, 0.3], thetas=[0, np.pi/4, np.pi/2, 3*np.pi/4]):
        """
        提取Gabor滤波器特征
        
        Args:
            image: 输入图像
            frequencies: 频率列表
            thetas: 角度列表
            
        Returns:
            Gabor特征向量
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        features = []
        
        # 对每个频率和角度计算Gabor特征
        for freq in frequencies:
            for theta in thetas:
                # 创建Gabor核
                kernel = cv2.getGaborKernel((21, 21), 5.0, theta, 1.0/freq, 0.5, 0, ktype=cv2.CV_32F)
                
                # 应用滤波器
                filtered = cv2.filter2D(gray, cv2.CV_8UC3, kernel)
                
                # 计算统计特征
                mean = np.mean(filtered)
                std = np.std(filtered)
                
                features.extend([mean, std])
        
        return np.array(features)
    
    def extract_deep_learning_features(self, image_path, model_name='resnet50'):
        """
        使用深度学习模型提取特征
        
        Args:
            image_path: 图像路径
            model_name: 模型名称
            
        Returns:
            深度学习特征向量
        """
        # 加载模型
        model = self.load_deep_learning_model(model_name)
        if model is None:
            return None
        
        # 图像预处理
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        # 读取图像并预处理
        img = Image.open(image_path).convert('RGB')
        img_tensor = preprocess(img).unsqueeze(0).to(self.device)
        
        # 提取特征
        with torch.no_grad():
            features = model(img_tensor)
        
        # 转换为numpy数组
        features = features.cpu().numpy().flatten()
        
        return features
    
    def visualize_keypoints(self, image, keypoints, output_path=None):
        """
        可视化关键点
        
        Args:
            image: 输入图像
            keypoints: 关键点列表
            output_path: 输出图像路径
            
        Returns:
            带有关键点的图像
        """
        # 绘制关键点
        img_with_keypoints = cv2.drawKeypoints(
            image, keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        
        # 保存结果
        if output_path:
            cv2.imwrite(output_path, img_with_keypoints)
        
        return img_with_keypoints
    
    def export_features(self, features_dict, output_path, format='json'):
        """
        导出特征到文件
        
        Args:
            features_dict: 特征字典
            output_path: 输出文件路径
            format: 输出格式
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if format == 'json':
            # 将numpy数组转换为列表以便JSON序列化
            serializable_dict = {}
            for file_path, features in features_dict.items():
                serializable_dict[file_path] = {}
                for feature_type, feature_value in features.items():
                    if isinstance(feature_value, np.ndarray):
                        serializable_dict[file_path][feature_type] = feature_value.tolist()
                    elif isinstance(feature_value, tuple) and len(feature_value) == 2:
                        # 对于SIFT/SURF/ORB特征，只保存描述符
                        _, descriptors = feature_value
                        if descriptors is not None:
                            serializable_dict[file_path][feature_type] = descriptors.tolist()
                        else:
                            serializable_dict[file_path][feature_type] = None
                    else:
                        serializable_dict[file_path][feature_type] = feature_value
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_dict, f, indent=2, ensure_ascii=False)
        elif format == 'csv':
            import csv
            # 找出所有特征类型
            all_feature_types = set()
            for features in features_dict.values():
                all_feature_types.update(features.keys())
            
            # 只保留向量类型的特征
            vector_feature_types = []
            for feature_type in all_feature_types:
                sample_value = None
                for features in features_dict.values():
                    if feature_type in features:
                        sample_value = features[feature_type]
                        break
                
                if isinstance(sample_value, np.ndarray):
                    vector_feature_types.append(feature_type)
            
            # 写入CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入表头
                headers = ['File_Path']
                for feature_type in vector_feature_types:
                    sample_value = None
                    for features in features_dict.values():
                        if feature_type in features:
                            sample_value = features[feature_type]
                            break
                    if sample_value is not None:
                        for i in range(len(sample_value)):
                            headers.append(f"{feature_type}_{i}")
                writer.writerow(headers)
                
                # 写入数据
                for file_path, features in features_dict.items():
                    row = [file_path]
                    for feature_type in vector_feature_types:
                        if feature_type in features and isinstance(features[feature_type], np.ndarray):
                            row.extend(features[feature_type].tolist())
                        else:
                            # 如果特征不存在，填充相同数量的NaN
                            sample_value = None
                            for f in features_dict.values():
                                if feature_type in f:
                                    sample_value = f[feature_type]
                                    break
                            if sample_value is not None and isinstance(sample_value, np.ndarray):
                                row.extend([float('nan')] * len(sample_value))
                    writer.writerow(row)
        else:
            print(f"不支持的导出格式: {format}")

def process_single_image(image_path, extractor, feature_types, visualize=False, output_dir=None):
    """处理单个图像"""
    try:
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        features = {}
        
        # 提取各种特征
        for feature_type in feature_types:
            if feature_type == 'hog':
                features['hog'] = extractor.extract_hog_features(image)
            elif feature_type == 'sift':
                kp, des = extractor.extract_sift_features(image)
                features['sift'] = (kp, des)
                # 可视化关键点
                if visualize and output_dir and kp:
                    base_name = os.path.basename(image_path)
                    name_without_ext = os.path.splitext(base_name)[0]
                    output_path = os.path.join(output_dir, f"{name_without_ext}_sift.jpg")
                    extractor.visualize_keypoints(image, kp, output_path)
            elif feature_type == 'surf':
                kp, des = extractor.extract_surf_features(image)
                features['surf'] = (kp, des)
                # 可视化关键点
                if visualize and output_dir and kp:
                    base_name = os.path.basename(image_path)
                    name_without_ext = os.path.splitext(base_name)[0]
                    output_path = os.path.join(output_dir, f"{name_without_ext}_surf.jpg")
                    extractor.visualize_keypoints(image, kp, output_path)
            elif feature_type == 'orb':
                kp, des = extractor.extract_orb_features(image)
                features['orb'] = (kp, des)
                # 可视化关键点
                if visualize and output_dir and kp:
                    base_name = os.path.basename(image_path)
                    name_without_ext = os.path.splitext(base_name)[0]
                    output_path = os.path.join(output_dir, f"{name_without_ext}_orb.jpg")
                    extractor.visualize_keypoints(image, kp, output_path)
            elif feature_type == 'lbp':
                features['lbp'] = extractor.extract_lbp_features(image)
            elif feature_type == 'color_histogram':
                features['color_histogram'] = extractor.extract_color_histogram(image)
            elif feature_type == 'color_moments':
                features['color_moments'] = extractor.extract_color_moments(image)
            elif feature_type == 'glcm':
                glcm_features = extractor.extract_glcm_features(image)
                if glcm_features is not None:
                    features['glcm'] = glcm_features
            elif feature_type == 'gabor':
                features['gabor'] = extractor.extract_gabor_features(image)
            elif feature_type.startswith('deep_'):
                # 深度学习特征
                model_name = feature_type[5:]  # 移除'deep_'前缀
                deep_features = extractor.extract_deep_learning_features(image_path, model_name)
                if deep_features is not None:
                    features[feature_type] = deep_features
            else:
                print(f"未知的特征类型: {feature_type}")
        
        return {os.path.abspath(image_path): features}
    except Exception as e:
        print(f"处理图像 {image_path} 时出错: {e}")
        return None

def process_directory(input_dir, extractor, feature_types, output_dir=None, recursive=False, visualize=False, image_extensions=None):
    """批量处理目录中的图像"""
    if image_extensions is None:
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    all_features = {}
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
                result = process_single_image(image_path, extractor, feature_types, visualize, output_dir)
                
                if result:
                    all_features.update(result)
                    processed_count += 1
                else:
                    failed_count += 1
    
    print(f"处理完成! 成功: {processed_count}, 失败: {failed_count}")
    return all_features

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='图像特征提取工具')
    parser.add_argument('--input', '-i', required=True, help='输入图像或目录路径')
    parser.add_argument('--output', '-o', default=None, help='输出目录路径')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
    
    # 特征类型参数
    parser.add_argument('--features', '-f', nargs='+', required=True,
                      choices=['hog', 'sift', 'surf', 'orb', 'lbp', 'color_histogram',
                              'color_moments', 'glcm', 'gabor', 'deep_resnet50', 'deep_vgg16',
                              'deep_inception_v3', 'deep_mobilenet_v2'],
                      help='要提取的特征类型')
    
    # 可视化参数
    parser.add_argument('--visualize', '-v', action='store_true', help='可视化特征（如关键点）')
    
    # 导出参数
    parser.add_argument('--export', '-e', default=None, help='导出特征文件路径')
    parser.add_argument('--export-format', default='json', choices=['json', 'csv'], help='导出格式')
    
    # 设备参数
    parser.add_argument('--device', default='auto', choices=['auto', 'cuda', 'cpu'], help='运行设备')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 确保输出目录存在
    if args.output and not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # 创建特征提取器
    extractor = FeatureExtractor(device=args.device)
    
    # 处理输入
    all_features = {}
    
    if os.path.isfile(args.input):
        # 处理单个文件
        result = process_single_image(args.input, extractor, args.features, args.visualize, args.output)
        if result:
            all_features.update(result)
            print(f"\n特征提取完成:")
            for file_path, features in result.items():
                print(f"文件: {file_path}")
                for feature_type, feature_value in features.items():
                    if isinstance(feature_value, np.ndarray):
                        print(f"  {feature_type}: 特征维度 = {len(feature_value)}")
                    elif isinstance(feature_value, tuple) and len(feature_value) == 2:
                        kp, des = feature_value
                        print(f"  {feature_type}: 关键点数量 = {len(kp)}, 描述符维度 = {des.shape if des is not None else 'None'}")
    elif os.path.isdir(args.input):
        # 处理目录
        all_features = process_directory(args.input, extractor, args.features, args.output, args.recursive, args.visualize)
    else:
        print(f"输入路径不存在: {args.input}")
        return
    
    # 导出特征
    if args.export and all_features:
        extractor.export_features(all_features, args.export, args.export_format)
        print(f"已导出特征到: {args.export}")

if __name__ == "__main__":
    main()
