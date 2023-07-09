resource "aws_instance" "ec2" {
  count = length(var.instance_group)
  instance_type = var.instance_group[count.index]
  ami = var.ami_id
  key_name = var.key_name
  availability_zone = var.availability_zone
  subnet_id = var.public_subnet_id
  iam_instance_profile   = var.ec2_instance_profile
  
  vpc_security_group_ids = [
    var.security_group_id
  ]

  tags = {
    "Name" = "${var.resource_prefix}_${var.instance_group[count.index]}"
  }

  user_data = <<-EOF
            #!/bin/bash
            sleep 30
            /home/ubuntu/get_cpuid/main
            aws s3 cp /home/ubuntu/get_cpuid/cpuid.csv s3://us-west-2-cpuid-x86/$(curl http://169.254.169.254/latest/meta-data/instance-type).csv
            sudo shutdown -h now
            EOF
}