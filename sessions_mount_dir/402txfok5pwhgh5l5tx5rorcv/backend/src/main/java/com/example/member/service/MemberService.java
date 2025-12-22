package com.example.member.service;

import com.example.member.entity.Member;
import com.example.member.repository.MemberRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class MemberService {

    private final MemberRepository memberRepository;

    @Autowired
    public MemberService(MemberRepository memberRepository) {
        this.memberRepository = memberRepository;
    }

    /**
     * 创建新会员
     * @param member 会员信息
     * @return 创建的会员
     */
    public Member createMember(Member member) {
        // 加密敏感信息
        member.setContact(encryptContact(member.getContact()));
        // 设置初始状态为活跃
        member.setStatus(Member.MemberStatus.ACTIVE);
        return memberRepository.save(member);
    }

    /**
     * 根据ID查询会员
     * @param id 会员ID
     * @return 会员信息
     */
    public Optional<Member> getMemberById(Long id) {
        return memberRepository.findById(id);
    }

    /**
     * 根据联系方式查询会员
     * @param contact 联系方式
     * @return 会员信息
     */
    public Optional<Member> getMemberByContact(String contact) {
        return memberRepository.findByContact(encryptContact(contact));
    }

    /**
     * 更新会员信息
     * @param id 会员ID
     * @param memberDetails 更新的会员信息
     * @return 更新后的会员
     */
    public Member updateMember(Long id, Member memberDetails) {
        Member member = memberRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Member not found with id: " + id));

        member.setName(memberDetails.getName());
        member.setContact(encryptContact(memberDetails.getContact()));
        member.setLevel(memberDetails.getLevel());
        member.setStatus(memberDetails.getStatus());

        return memberRepository.save(member);
    }

    /**
     * 删除会员
     * @param id 会员ID
     */
    public void deleteMember(Long id) {
        memberRepository.deleteById(id);
    }

    /**
     * 获取所有会员
     * @return 会员列表
     */
    public List<Member> getAllMembers() {
        return memberRepository.findAll();
    }

    /**
     * 根据状态查询会员
     * @param status 会员状态
     * @return 会员列表
     */
    public List<Member> getMembersByStatus(Member.MemberStatus status) {
        return memberRepository.findByStatus(status);
    }

    /**
     * 根据等级查询会员
     * @param level 会员等级
     * @return 会员列表
     */
    public List<Member> getMembersByLevel(Member.MemberLevel level) {
        return memberRepository.findByLevel(level);
    }

    /**
     * 根据姓名模糊查询会员
     * @param name 会员姓名
     * @return 会员列表
     */
    public List<Member> getMembersByNameContaining(String name) {
        return memberRepository.findByNameContaining(name);
    }

    /**
     * 获取所有活跃会员
     * @return 活跃会员列表
     */
    public List<Member> getAllActiveMembers() {
        return memberRepository.findAllActiveMembers();
    }

    /**
     * 冻结会员
     * @param id 会员ID
     * @return 更新后的会员
     */
    public Member freezeMember(Long id) {
        Member member = memberRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Member not found with id: " + id));
        member.setStatus(Member.MemberStatus.FROZEN);
        return memberRepository.save(member);
    }

    /**
     * 激活会员
     * @param id 会员ID
     * @return 更新后的会员
     */
    public Member activateMember(Long id) {
        Member member = memberRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Member not found with id: " + id));
        member.setStatus(Member.MemberStatus.ACTIVE);
        return memberRepository.save(member);
    }

    /**
     * 标记会员为过期
     * @param id 会员ID
     * @return 更新后的会员
     */
    public Member expireMember(Long id) {
        Member member = memberRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Member not found with id: " + id));
        member.setStatus(Member.MemberStatus.EXPIRED);
        return memberRepository.save(member);
    }

    /**
     * 统计各会员等级的会员数量
     * @return 会员等级统计结果
     */
    public List<Object[]> countMembersByLevel() {
        return memberRepository.countMembersByLevel();
    }

    /**
     * 统计各会员状态的会员数量
     * @return 会员状态统计结果
     */
    public List<Object[]> countMembersByStatus() {
        return memberRepository.countMembersByStatus();
    }

    /**
     * 加密联系方式
     * @param contact 原始联系方式
     * @return 加密后的联系方式
     */
    private String encryptContact(String contact) {
        // 这里使用简单的Base64编码作为示例，实际项目中应使用更安全的加密方式
        return java.util.Base64.getEncoder().encodeToString(contact.getBytes());
    }

    /**
     * 解密联系方式
     * @param encryptedContact 加密后的联系方式
     * @return 原始联系方式
     */
    private String decryptContact(String encryptedContact) {
        return new String(java.util.Base64.getDecoder().decode(encryptedContact));
    }
}
