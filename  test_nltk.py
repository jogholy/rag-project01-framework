import nltk
import os
from pathlib import Path

print(f"NLTK data path: {nltk.data.path}")

try:
    print("\nAttempting to find 'tokenizers/punkt'...")
    punkt_path = nltk.find('tokenizers/punkt')
    print(f"Found punkt at: {punkt_path}")
    
    # 检查punkt是否是目录
    if Path(punkt_path).is_dir():
        print("Punkt is a directory (expected). Checking directory integrity...")
        # 尝试读取英文语言文件
        english_pickle = Path(punkt_path) / 'english.pickle'
        if english_pickle.exists():
            with open(english_pickle, 'rb') as f:
                f.read(1)  # 尝试读取一个字节
            print("Punkt directory and English model seem ok.")
        else:
            print("English model not found in punkt directory!")
            raise FileNotFoundError("Missing English model in punkt directory")

    print("\nAttempting to tokenize sentence...")
    sentences = nltk.sent_tokenize("This is sentence one. This is sentence two.")
    print("Sentence tokenization successful.")

    print("\nAttempting to find 'taggers/averaged_perceptron_tagger'...")
    tagger_path = nltk.find('taggers/averaged_perceptron_tagger')
    print(f"Found tagger at: {tagger_path}")
    
    # 检查tagger是否是目录
    if Path(tagger_path).is_dir():
        print("Tagger is a directory (expected). Checking directory integrity...")
        # 尝试读取主模型文件
        model_file = Path(tagger_path) / 'averaged_perceptron_tagger.pickle'
        if model_file.exists():
            with open(model_file, 'rb') as f:
                f.read(1)  # 尝试读取一个字节
            print("Tagger directory and model seem ok.")
        else:
            print("Tagger model not found!")
            raise FileNotFoundError("Missing tagger model")

    print("\nAttempting POS tagging...")
    tagged = nltk.pos_tag(nltk.word_tokenize("This is a test."))
    print("POS tagging successful.")

    print("\nNLTK check passed!")

except Exception as e:
    print(f"\n--- NLTK Check FAILED ---")
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")